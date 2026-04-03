from arb_bot.engine.sizing import balanced_sizes, has_two_sided_edge
from arb_bot.models import Opportunity

def evaluate_two_way_arb(*, event_key: str, yes_platform: str, no_platform: str, yes_price: float, no_price: float, max_yes_size: float, max_no_size: float, fee_buffer: float = 0.0) -> Opportunity | None:
    if not has_two_sided_edge(yes_price, no_price, fee_buffer):
        return None

    s = balanced_sizes(yes_price, no_price, max_yes_size, max_no_size)
    if s.profit_if_yes <= 0 or s.profit_if_no <= 0:
        return None

    return Opportunity(
        event_key=event_key,
        buy_yes_platform=yes_platform,
        buy_no_platform=no_platform,
        yes_price=yes_price,
        no_price=no_price,
        yes_size=s.yes_size,
        no_size=s.no_size,
        profit_if_yes=s.profit_if_yes,
        profit_if_no=s.profit_if_no,
    )
