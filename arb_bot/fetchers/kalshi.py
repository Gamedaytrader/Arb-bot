"""
Kalshi API client.
 
Public (read) endpoints require no auth.
Order execution requires KALSHI_API_KEY in env.
 
Docs: https://trading-api.readme.io/reference/getmarkets
"""
import logging
import time
from datetime import datetime
from typing import Optional
 
import requests
 
from arb_bot.config import KALSHI_API_KEY, KALSHI_BASE_URL
from arb_bot.models import OrderLevel, RawMarket
 
logger = logging.getLogger(__name__)
 
_SESSION = requests.Session()
_SESSION.headers.update({"Accept": "application/json"})
 
 
def _get(path: str, params: Optional[dict] = None, retries: int = 4) -> dict:
    """GET with exponential backoff on 429 / 5xx."""
    url = KALSHI_BASE_URL + path
    delay = 2
    for attempt in range(retries + 1):
        try:
            resp = _SESSION.get(url, params=params, timeout=10)
            if resp.status_code == 429:
                logger.warning("Kalshi rate-limited, waiting %ds", delay)
                time.sleep(delay)
                delay *= 2
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            if attempt == retries:
                raise
            logger.warning("Kalshi request failed (%s), retrying in %ds", exc, delay)
            time.sleep(delay)
            delay *= 2
    return {}
 
 
def _parse_close_time(raw: dict) -> Optional[datetime]:
    ts = raw.get("close_time") or raw.get("expiration_time")
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
 
 
def fetch_markets(limit: int = 200) -> list[RawMarket]:
    """
    Fetch open Kalshi markets and return them as RawMarket objects.
 
    Kalshi returns prices in cents (0-100).  We divide by 100 to get (0-1).
    yes_ask  = best price to BUY YES (what you pay per share)
    no_ask   = best price to BUY NO
 
    Markets missing ask prices on either side are skipped.
    Orderbook depth is fetched lazily only for matched pairs.
    """
    markets: list[RawMarket] = []
    cursor: Optional[str] = None
 
    while True:
        params: dict = {"status": "open", "limit": min(limit, 200)}
        if cursor:
            params["cursor"] = cursor
 
        data = _get("/markets", params=params)
        raw_markets = data.get("markets", [])
 
        for m in raw_markets:
            ticker = m.get("ticker", "")
            title = m.get("title", "") or m.get("subtitle", "") or ticker
 
            # Prices in Kalshi are 0-99 cents; normalise to 0-1 probability
            yes_ask_raw = m.get("yes_ask")
            no_ask_raw = m.get("no_ask")
 
            if yes_ask_raw is None or no_ask_raw is None:
                continue
 
            yes_ask = yes_ask_raw / 100.0
            no_ask = no_ask_raw / 100.0
 
            if not (0 < yes_ask < 1) or not (0 < no_ask < 1):
                continue
 
            markets.append(
                RawMarket(
                    platform="kalshi",
                    market_id=ticker,
                    title=title,
                    yes_ask=yes_ask,
                    no_ask=no_ask,
                    close_time=_parse_close_time(m),
                    meta={"kalshi_ticker": ticker},
                )
            )
 
        cursor = data.get("cursor")
        if not cursor or len(raw_markets) < 200:
            break
 
    logger.info("Kalshi: fetched %d open markets", len(markets))
    return markets
 
 
def fetch_orderbook(ticker: str) -> tuple[list[OrderLevel], list[OrderLevel]]:
    """
    Fetch YES and NO orderbook depth for a Kalshi market.
 
    Returns (yes_asks, no_asks) — ascending price order so simulate_fill works.
 
    Kalshi orderbook format:
        {"orderbook": {"yes": [[price_cents, qty], ...], "no": [[price_cents, qty], ...]}}
    """
    data = _get(f"/markets/{ticker}/orderbook")
    ob = data.get("orderbook", {})
 
    def parse_side(raw_levels: list) -> list[OrderLevel]:
        levels = []
        for entry in raw_levels or []:
            if len(entry) < 2:
                continue
            price = entry[0] / 100.0
            qty = float(entry[1])
            if 0 < price < 1 and qty > 0:
                levels.append(OrderLevel(price=price, size=qty))
        # Sort ascending so cheapest ask is first
        return sorted(levels, key=lambda x: x.price)
 
    yes_levels = parse_side(ob.get("yes", []))
    no_levels = parse_side(ob.get("no", []))
    return yes_levels, no_levels
 
 
def place_order(
    ticker: str,
    side: str,        # "yes" or "no"
    count: int,       # number of contracts
    price_cents: int, # limit price 1-99
    dry_run: bool = True,
) -> dict:
    """
    Place a limit order on Kalshi.
 
    Requires KALSHI_API_KEY set in environment.
    Always no-ops unless dry_run=False is explicitly passed.
    """
    payload = {
        "ticker": ticker,
        "side": side,
        "count": count,
        "type": "limit",
        "yes_price": price_cents if side == "yes" else 100 - price_cents,
    }
    if dry_run:
        logger.info("[DRY RUN] Would place Kalshi order: %s", payload)
        return {"dry_run": True, "payload": payload}
 
    if not KALSHI_API_KEY:
        raise RuntimeError("KALSHI_API_KEY not set — cannot place live orders")
 
    auth_session = requests.Session()
    auth_session.headers.update({
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Token {KALSHI_API_KEY}",
    })
    resp = auth_session.post(
        KALSHI_BASE_URL + "/portfolio/orders",
        json=payload,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()
