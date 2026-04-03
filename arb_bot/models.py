from dataclasses import dataclass
from datetime import datetime

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
class Market:
    platform: str
    market_id: str
    event_key: str
    title: str
    start_time: datetime

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
