from arb_bot.engine.orderbook import simulate_fill
from arb_bot.models import OrderLevel

def test_vwap():
    levels = [OrderLevel(0.48, 200), OrderLevel(0.49, 300), OrderLevel(0.50, 500)]
    r = simulate_fill(levels, 1000)
    assert r.filled_size == 1000
    assert abs(r.average_price - 0.493) < 1e-9
