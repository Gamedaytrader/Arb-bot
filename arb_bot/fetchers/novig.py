"""
Novig GraphQL client.
 
All read endpoints are public — no auth required.
Order execution requires NOVIG_OAUTH_TOKEN in env.
 
GraphQL endpoint: https://gql.novig.us/v1/graphql
"""
import logging
import time
from datetime import datetime
from typing import Optional
 
import requests
 
from arb_bot.config import NOVIG_GQL_URL, NOVIG_OAUTH_TOKEN
from arb_bot.models import OrderLevel, RawMarket
 
logger = logging.getLogger(__name__)
 
_SESSION = requests.Session()
_SESSION.headers.update({
    "Content-Type": "application/json",
    "Accept": "application/json",
})
 
# GraphQL query to fetch open markets.
# Field names are based on Novig's public schema; adjust if schema changes.
_MARKETS_QUERY = """
query OpenMarkets($limit: Int!) {
  markets(
    where: { status: { _eq: "open" } }
    limit: $limit
    order_by: { volume_24h: desc }
  ) {
    id
    title
    description
    probability
    yes_ask
    no_ask
    yes_volume
    no_volume
    closes_at
  }
}
"""
 
# Fallback query with minimal fields if the schema differs
_MARKETS_QUERY_MINIMAL = """
query OpenMarkets($limit: Int!) {
  markets(where: { status: { _eq: "open" } }, limit: $limit) {
    id
    title
    probability
    closes_at
  }
}
"""
 
 
def _gql(query: str, variables: Optional[dict] = None, retries: int = 4) -> dict:
    """POST a GraphQL query with exponential backoff on errors."""
    payload = {"query": query, "variables": variables or {}}
    delay = 2
    for attempt in range(retries + 1):
        try:
            resp = _SESSION.post(NOVIG_GQL_URL, json=payload, timeout=10)
            if resp.status_code == 429:
                logger.warning("Novig rate-limited, waiting %ds", delay)
                time.sleep(delay)
                delay *= 2
                continue
            resp.raise_for_status()
            body = resp.json()
            if "errors" in body:
                logger.warning("Novig GraphQL errors: %s", body["errors"])
            return body
        except requests.RequestException as exc:
            if attempt == retries:
                raise
            logger.warning("Novig request failed (%s), retrying in %ds", exc, delay)
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
 
 
def fetch_markets(limit: int = 200) -> list[RawMarket]:
    """
    Fetch open Novig markets.
 
    Novig probability fields are already in (0-1) range.
    yes_ask / no_ask are direct probabilities to buy YES/NO.
    Falls back to deriving no_ask from probability if explicit fields are absent.
    """
    body = _gql(_MARKETS_QUERY, {"limit": limit})
    raw_markets = (body.get("data") or {}).get("markets", [])
 
    # If the full query failed (schema mismatch), try the minimal fallback
    if not raw_markets and "errors" in body:
        logger.info("Novig: retrying with minimal query")
        body = _gql(_MARKETS_QUERY_MINIMAL, {"limit": limit})
        raw_markets = (body.get("data") or {}).get("markets", [])
 
    markets: list[RawMarket] = []
    for m in raw_markets:
        market_id = str(m.get("id", ""))
        title = m.get("title") or m.get("description") or market_id
        if not market_id or not title:
            continue
 
        probability = m.get("probability")
        yes_ask = m.get("yes_ask") or probability
        no_ask = m.get("no_ask")
 
        # Derive no_ask from probability if not explicit
        if yes_ask is None:
            continue
        if no_ask is None:
            no_ask = 1.0 - float(yes_ask)
 
        try:
            yes_ask = float(yes_ask)
            no_ask = float(no_ask)
        except (TypeError, ValueError):
            continue
 
        if not (0 < yes_ask < 1) or not (0 < no_ask < 1):
            continue
 
        # Volume fields give us a rough liquidity estimate
        yes_vol = float(m.get("yes_volume") or 0)
        no_vol = float(m.get("no_volume") or 0)
 
        markets.append(
            RawMarket(
                platform="novig",
                market_id=market_id,
                title=title,
                yes_ask=yes_ask,
                no_ask=no_ask,
                yes_liquidity=yes_vol,
                no_liquidity=no_vol,
                close_time=_parse_close_time(m.get("closes_at")),
                meta={"novig_id": market_id},
            )
        )
 
    logger.info("Novig: fetched %d open markets", len(markets))
    return markets
 
 
def fetch_orderbook(market_id: str) -> tuple[list[OrderLevel], list[OrderLevel]]:
    """
    Fetch YES and NO orderbook depth from Novig.
 
    Expected response structure (adjust if schema differs):
        { "data": { "market_orderbook": { "yes": [...], "no": [...] } } }
 
    Each level: { "price": 0.48, "size": 200 }
    """
    query = """
    query Orderbook($id: String!) {
      market_orderbook(market_id: $id) {
        yes { price size }
        no  { price size }
      }
    }
    """
    body = _gql(query, {"id": market_id})
    ob = ((body.get("data") or {}).get("market_orderbook") or {})
 
    def parse_side(raw: list) -> list[OrderLevel]:
        levels = []
        for entry in raw or []:
            price = float(entry.get("price", 0))
            size = float(entry.get("size", 0))
            if 0 < price < 1 and size > 0:
                levels.append(OrderLevel(price=price, size=size))
        return sorted(levels, key=lambda x: x.price)
 
    return parse_side(ob.get("yes", [])), parse_side(ob.get("no", []))
 
 
def place_order(
    market_id: str,
    side: str,        # "yes" or "no"
    size: float,
    price: float,     # 0-1
    dry_run: bool = True,
) -> dict:
    """Place an order on Novig (requires NOVIG_OAUTH_TOKEN)."""
    payload = {
        "market_id": market_id,
        "side": side,
        "size": size,
        "price": price,
        "type": "limit",
    }
    if dry_run:
        logger.info("[DRY RUN] Would place Novig order: %s", payload)
        return {"dry_run": True, "payload": payload}
 
    if not NOVIG_OAUTH_TOKEN:
        raise RuntimeError("NOVIG_OAUTH_TOKEN not set — cannot place live orders")
 
    auth_session = requests.Session()
    auth_session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {NOVIG_OAUTH_TOKEN}",
    })
    resp = auth_session.post(
        "https://api.novig.us/v1/orders",
        json=payload,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()
