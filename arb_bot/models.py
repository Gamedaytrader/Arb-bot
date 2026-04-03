from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class OrderLevel:
    price: float
    size: float


@dataclass(frozen=True)
class FillResult:
    requested_size: float
    filled_size: float
    average_price: float
    total_cost: float
    partial: bool


@dataclass(frozen=True)
class Opportunity:
    event_key: str
    buy_yes_platform: str
    buy_no_platform: str
    yes_price: float
    no_price: float
    yes_size: float
    no_size: float
    profit_if_yes: float
    profit_if_no: float


@dataclass
class RawMarket:
    """Lightweight market snapshot fetched from a platform's market-list endpoint."""
    platform: str
    market_id: str
    title: str
    yes_ask: float
    no_ask: float
    yes_liquidity: float = 0.0
    no_liquidity: float = 0.0
    close_time: Optional[datetime] = None
    meta: dict = field(default_factory=dict)
