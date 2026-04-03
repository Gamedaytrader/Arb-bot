"""Polymarket public-read fetcher placeholder."""
"""
Polymarket client.
 
All read endpoints are public — no auth required.
Execution requires a Polygon wallet + USDC (Phase 4).
 
Gamma API (market metadata): https://gamma-api.polymarket.com
CLOB API (orderbook):        https://clob.polymarket.com
"""
import json
import logging
import time
from datetime import datetime
from typing import Optional
 
import requests
 
from arb_bot.config import POLYMARKET_CLOB_URL, POLYMARKET_GAMMA_URL
from arb_bot.models import OrderLevel, RawMarket
 
logger = logging.getLogger(__name__)
 
_SESSION = requests.Session()
_SESSION.headers.update({"Accept": "application/json"})
 
 
def _get(base: str, path: str, params: Optional[dict] = None, retries: int = 4) -> dict | list:
    url = base + path
    delay = 2
    for attempt in range(retries + 1):
        try:
            resp = _SESSION.get(url, params=params, timeout=10)
            if resp.status_code == 429:
                logger.warning("Polymarket rate-limited, waiting %ds", delay)
                time.sleep(delay)
                delay *= 2
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            if attempt == retries:
                raise
            logger.warning("Polymarket request failed (%s), retrying in %ds", exc, delay)
            time.sleep(delay)
            delay *= 2
    return {}
 
 
def _post(base: str, path: str, payload: dict, retries: int = 4) -> dict | list:
    url = base + path
    delay = 2
    for attempt in range(retries + 1):
        try:
            resp = _SESSION.post(url, json=payload, timeout=10)
            if resp.status_code == 429:
                logger.warning("Polymarket CLOB rate-limited, waiting %ds", delay)
                time.sleep(delay)
                delay *= 2
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            if attempt == retries:
                raise
            logger.warning("Polymarket CLOB request failed (%s), retrying in %ds", exc, delay)
            time.sleep(delay)
            delay *= 2
    return {}
 
 
def _parse_close_time(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
 
 
def _parse_json_field(value) -> list:
    """Parse a field that may be a JSON string or already a list."""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return []
    return []
 
 
def fetch_markets(limit: int = 100) -> list[RawMarket]:
    """
    Fetch active Polymarket markets from the Gamma API.
 
    Response fields of interest:
      - id             : internal market ID
      - question       : human-readable question (used for matching)
      - outcomePrices  : JSON string like '["0.52", "0.48"]' (YES=index 0)
      - clobTokenIds   : JSON string array of CLOB token IDs (YES=index 0)
      - endDate        : ISO timestamp
      - active         : bool
      - volume         : total volume (rough liquidity signal)
    """
    params = {"active": "true", "limit": limit, "closed": "false"}
    data = _get(POLYMARKET_GAMMA_URL, "/markets", params=params)
 
    # Gamma API may return a list directly or {"markets": [...]}
    if isinstance(data, list):
        raw_markets = data
    else:
        raw_markets = data.get("markets", []) if isinstance(data, dict) else []
 
    markets: list[RawMarket] = []
    for m in raw_markets:
        market_id = str(m.get("id", ""))
        title = m.get("question") or m.get("title") or market_id
        if not market_id:
            continue
 
        outcome_prices = _parse_json_field(m.get("outcomePrices", "[]"))
        clob_token_ids = _parse_json_field(m.get("clobTokenIds", "[]"))
 
        if len(outcome_prices) < 2:
            continue
 
        try:
            yes_ask = float(outcome_prices[0])
            no_ask = float(outcome_prices[1])
        except (ValueError, TypeError):
            continue
 
        if not (0 < yes_ask < 1) or not (0 < no_ask < 1):
            continue
 
        volume = float(m.get("volume") or 0)
 
        markets.append(
            RawMarket(
                platform="polymarket",
                market_id=market_id,
                title=title,
                yes_ask=yes_ask,
                no_ask=no_ask,
                yes_liquidity=volume / 2,   # rough estimate; use CLOB for precision
                no_liquidity=volume / 2,
                close_time=_parse_close_time(m.get("endDate")),
                meta={
                    "clob_yes_token": clob_token_ids[0] if len(clob_token_ids) > 0 else "",
                    "clob_no_token": clob_token_ids[1] if len(clob_token_ids) > 1 else "",
                },
            )
        )
 
    logger.info("Polymarket: fetched %d active markets", len(markets))
    return markets
 
 
def fetch_orderbook(token_id: str) -> tuple[list[OrderLevel], list[OrderLevel]]:
    """
    Fetch YES-side orderbook depth for a Polymarket CLOB token.
 
    POST /books with {"token_id": "<token_id>"}
 
    Response: {"bids": [{"price": "0.48", "size": "200"}, ...],
               "asks": [{"price": "0.52", "size": "150"}, ...]}
 
    To buy YES: walk the asks (ascending price).
    """
    data = _post(POLYMARKET_CLOB_URL, "/books", {"token_id": token_id})
    if isinstance(data, list) and data:
        data = data[0]
 
    def parse_asks(raw: list) -> list[OrderLevel]:
        levels = []
        for entry in raw or []:
            try:
                price = float(entry.get("price", 0))
                size = float(entry.get("size", 0))
            except (TypeError, ValueError):
                continue
            if 0 < price < 1 and size > 0:
                levels.append(OrderLevel(price=price, size=size))
        return sorted(levels, key=lambda x: x.price)
 
    yes_asks = parse_asks(data.get("asks", []) if isinstance(data, dict) else [])
    return yes_asks, []  # CLOB returns one token side; call separately for NO token
