from typing import Iterable
from arb_bot.models import FillResult, OrderLevel

class InsufficientLiquidityError(ValueError):
    pass

def simulate_fill(levels: Iterable[OrderLevel], target_size: float) -> FillResult:
    if target_size <= 0:
        raise ValueError("target_size must be > 0")

    remaining = target_size
    total_cost = 0.0
    filled = 0.0

    for level in levels:
        if remaining <= 0:
            break
        if level.size <= 0:
            continue
        take = min(level.size, remaining)
        total_cost += take * level.price
        filled += take
        remaining -= take

    if filled == 0:
        raise InsufficientLiquidityError("No fillable liquidity in orderbook")

    return FillResult(
        requested_size=target_size,
        filled_size=filled,
        average_price=total_cost / filled,
        total_cost=total_cost,
        partial=filled < target_size,
    )
