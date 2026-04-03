from dataclasses import dataclass
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
 
@dataclass(frozen=True)
class OrderLevel:

Expand 27 hidden lines
    no_size: float
    profit_if_yes: float
    profit_if_no: float
 
@dataclass
class RawMarket:
    """Lightweight market snapshot fetched from a platform's market-list endpoint."""
    platform: str
    market_id: str
    title: str          # used for fuzzy matching across platforms
    yes_ask: float      # probability (0-1) to buy YES at best ask
    no_ask: float       # probability (0-1) to buy NO at best ask
    yes_liquidity: float = 0.0   # USD depth available near best ask (YES side)
    no_liquidity: float = 0.0    # USD depth available near best ask (NO side)
    close_time: Optional[datetime] = None
    # platform-specific extra data (e.g. Polymarket token IDs)
    meta: dict = field(default_factory=dict)
