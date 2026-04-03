"""Discord webhook alerting."""
import logging
from datetime import datetime, timezone
 
import requests
 
from arb_bot.config import DISCORD_WEBHOOK_URL
from arb_bot.models import RawMarket
 
logger = logging.getLogger(__name__)
 
 
def _post_webhook(payload: dict) -> None:
    if not DISCORD_WEBHOOK_URL:
        logger.warning("DISCORD_WEBHOOK_URL not set — skipping Discord alert")
        return
    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Discord webhook failed: %s", exc)
 
 
def send_arb_alert(
    yes_market: RawMarket,
    no_market: RawMarket,
    edge: float,
    max_bet: float,
    expected_profit: float,
    dry_run: bool = True,
) -> None:
    """
    Send an arb opportunity alert to Discord.
 
    Format:
        🎯 ARB DETECTED — 5.2% edge
        <title> | <platforms>
 
        BUY YES on <platform> @ <price>  ($<liq> available)
        BUY NO  on <platform> @ <price>  ($<liq> available)
 
        Max bet: $<amount>  (liquidity constrained)
        Expected profit: $<profit> on $<bet> risked (<edge>%)
        Time: <timestamp>
        [DRY RUN — no orders placed]
    """
    now = datetime.now(timezone.utc).strftime("%I:%M:%S %p UTC")
    edge_pct = edge * 100
 
    lines = [
        f"**{'[DRY RUN] ' if dry_run else ''}🎯 ARB DETECTED — {edge_pct:.1f}% edge**",
        f"{yes_market.title}",
        f"Platforms: **{yes_market.platform.upper()}** vs **{no_market.platform.upper()}**",
        "",
        f"BUY YES on **{yes_market.platform}** @ `{yes_market.yes_ask:.3f}`"
        f"  (${yes_market.yes_liquidity:.0f} available)",
        f"BUY NO  on **{no_market.platform}** @ `{no_market.no_ask:.3f}`"
        f"  (${no_market.no_liquidity:.0f} available)",
        "",
        f"Max bet: **${max_bet:.2f}**",
        f"Expected profit: **${expected_profit:.2f}** on ${max_bet:.2f} risked ({edge_pct:.1f}%)",
        f"Time detected: {now}",
    ]
    if dry_run:
        lines.append("_DRY RUN — no orders placed_")
 
    payload = {"content": "\n".join(lines)}
    _post_webhook(payload)
    logger.info(
        "Discord alert sent: %s edge=%.1f%% bet=$%.2f profit=$%.2f",
        yes_market.title,
        edge_pct,
        max_bet,
        expected_profit,
    )
 
 
def send_error_alert(message: str) -> None:
    """Send a simple error/status message to Discord."""
    payload = {"content": f"⚠️ **Arb Bot Error**: {message}"}
    _post_webhook(payload)
