from dataclasses import dataclass

@dataclass(frozen=True)
class SizingResult:
    yes_size: float
    no_size: float
    profit_if_yes: float
    profit_if_no: float

def has_two_sided_edge(yes_price: float, no_price: float, fees: float = 0.0) -> bool:
    return yes_price + no_price + fees < 1.0

def balanced_sizes(yes_price: float, no_price: float, max_yes_size: float, max_no_size: float) -> SizingResult:
    if not (0 < yes_price < 1 and 0 < no_price < 1):
        raise ValueError("prices must be in (0,1)")
    if max_yes_size <= 0 or max_no_size <= 0:
        raise ValueError("max sizes must be > 0")

    size = min(max_yes_size, max_no_size)
    profit_if_yes = size * (1 - yes_price) - size * no_price
    profit_if_no = size * (1 - no_price) - size * yes_price
    return SizingResult(size, size, profit_if_yes, profit_if_no)
