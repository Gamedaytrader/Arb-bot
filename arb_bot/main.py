from arb_bot.engine.sizing import balanced_sizes, has_two_sided_edge
from arb_bot.fetchers import kalshi, novig, polymarket
from arb_bot.matching.event_matcher import MarketPair, find_matches
from arb_bot.models import RawMarket
from arb_bot.utils.discord import send_arb_alert, send_error_alert
from arb_bot.utils.logger import setup_logging
 
logger = logging.getLogger(__name__)
 
 
def fetch_all_markets() -> dict[str, list[RawMarket]]:
    """Fetch markets from all platforms, returning per-platform lists."""
    results: dict[str, list[RawMarket]] = {}
    fetchers = {
        "kalshi": kalshi.fetch_markets,
        "novig": novig.fetch_markets,
        "polymarket": polymarket.fetch_markets,
    }
    for name, fn in fetchers.items():
        try:
            results[name] = fn()
        except Exception as exc:
            logger.error("Failed to fetch %s markets: %s", name, exc)
            results[name] = []
    return results
 
 
def evaluate_pair(pair: MarketPair) -> None:
    """
    Check a matched market pair for arbitrage.
 
    Uses the best-ask prices from the market list (no orderbook call needed
    for detection).  Logs and alerts if an opportunity is found.
    """
    a = pair.market_a
    b = pair.market_b
 
    # --- Check A-YES / B-NO direction ---
    _check_direction(
        yes_market=a,
        no_market=b,
        yes_price=a.yes_ask,
        no_price=b.no_ask,
        yes_liq=a.yes_liquidity,
        no_liq=b.no_liquidity,
        match_score=pair.match_score,
    )
 
    # --- Check B-YES / A-NO direction ---
    _check_direction(
        yes_market=b,
        no_market=a,
        yes_price=b.yes_ask,
        no_price=a.no_ask,
        yes_liq=b.yes_liquidity,
        no_liq=a.no_liquidity,
        match_score=pair.match_score,
    )
 
 
def _check_direction(
    yes_market: RawMarket,
    no_market: RawMarket,
    yes_price: float,
    no_price: float,
    yes_liq: float,
    no_liq: float,
    match_score: float,
) -> None:
    edge = 1.0 - yes_price - no_price
    if edge < MIN_EDGE:
        return
 
    min_liq = min(yes_liq, no_liq)
    if min_liq < MIN_LIQUIDITY_USD and min_liq > 0:
        logger.debug(
            "Skipping arb %s/%s edge=%.1f%% — liquidity too low ($%.0f)",
            yes_market.platform,
            no_market.platform,
            edge * 100,
            min_liq,
        )
        return
 
    # Cap bet size to MAX_BET_SIZE and 30% of available liquidity
    max_from_liq = min(yes_liq, no_liq) * 0.3 if min_liq > 0 else MAX_BET_SIZE
    max_bet = min(MAX_BET_SIZE, max_from_liq)
    if max_bet <= 0:
        max_bet = MAX_BET_SIZE  # fallback when liquidity unknown
 
    sizing = balanced_sizes(
        yes_price=yes_price,
        no_price=no_price,
        max_yes_size=max_bet,
        max_no_size=max_bet,
    )
 
    if sizing.profit_if_yes <= 0 or sizing.profit_if_no <= 0:
        return
 
    expected_profit = min(sizing.profit_if_yes, sizing.profit_if_no)
 
    logger.info(
        "ARB FOUND  edge=%.1f%%  %s YES@%.3f / %s NO@%.3f  "
        "bet=$%.2f  profit=$%.2f  match=%.0f%%  title='%s'",
        edge * 100,
        yes_market.platform,
        yes_price,
        no_market.platform,
        no_price,
        max_bet,
        expected_profit,
        match_score,
        yes_market.title,
    )
 
    if DRY_RUN:
        logger.info(
            "[DRY RUN] Would BUY YES on %s market_id=%s @ %.3f  size=$%.2f",
            yes_market.platform,
            yes_market.market_id,
            yes_price,
            max_bet,
        )
        logger.info(
            "[DRY RUN] Would BUY NO  on %s market_id=%s @ %.3f  size=$%.2f",
            no_market.platform,
            no_market.market_id,
            no_price,
            max_bet,
        )
 
    send_arb_alert(
        yes_market=yes_market,
        no_market=no_market,
        edge=edge,
        max_bet=max_bet,
        expected_profit=expected_profit,
        dry_run=DRY_RUN,
    )
 
 
def run_cycle() -> None:
    """Execute one full scan cycle."""
    start = time.monotonic()
    logger.info("--- Scan cycle starting ---")
 
    all_markets = fetch_all_markets()
    total = sum(len(v) for v in all_markets.values())
    logger.info(
        "Fetched %d markets total: kalshi=%d novig=%d polymarket=%d",
        total,
        len(all_markets.get("kalshi", [])),
        len(all_markets.get("novig", [])),
        len(all_markets.get("polymarket", [])),
    )
 
    # Cross-match every platform pair
    platform_names = [p for p, mlist in all_markets.items() if mlist]
    pairs_checked = 0
    opps_found = 0
 
    for p1, p2 in itertools.combinations(platform_names, 2):
        matches = find_matches(
            all_markets[p1],
            all_markets[p2],
            threshold=MATCH_THRESHOLD,
        )
        logger.info("Matched %d pairs: %s <-> %s", len(matches), p1, p2)
        for pair in matches:
            pairs_checked += 1
            evaluate_pair(pair)
 
    elapsed = time.monotonic() - start
    logger.info(
        "--- Cycle done in %.1fs  pairs_checked=%d ---",
        elapsed,
        pairs_checked,
    )
    setup_logging()
    logger.info(
        "Arb bot starting  DRY_RUN=%s  MIN_EDGE=%.1f%%  POLL_INTERVAL=%ds",
        DRY_RUN,
        MIN_EDGE * 100,
        POLL_INTERVAL,
    )
    if DRY_RUN:
        logger.info("Running in DRY RUN mode — no live orders will be placed")
 
    while True:
        try:
            run_cycle()
        except KeyboardInterrupt:
            logger.info("Shutting down")
            break
        except Exception as exc:
            logger.exception("Unhandled error in scan cycle: %s", exc)
            try:
                send_error_alert(str(exc))
            except Exception:
                pass
 
        time.sleep(POLL_INTERVAL)
 
 
if __name__ == "__main__":
    main()
