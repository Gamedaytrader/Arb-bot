from arb_bot.engine.arb import evaluate_two_way_arb
from arb_bot.engine.orderbook import simulate_fill
from arb_bot.models import OrderLevel

def main() -> None:
    novig = [OrderLevel(0.48, 200), OrderLevel(0.49, 300), OrderLevel(0.50, 500)]
    kalshi = [OrderLevel(0.53, 700), OrderLevel(0.54, 1000)]

    f_yes = simulate_fill(novig, 500)
    f_no = simulate_fill(kalshi, 450)

    opp = evaluate_two_way_arb(
        event_key="nba:lakers-warriors",
        yes_platform="novig",
        no_platform="kalshi",
        yes_price=f_yes.average_price,
        no_price=f_no.average_price,
        max_yes_size=f_yes.filled_size,
        max_no_size=f_no.filled_size,
        fee_buffer=0.005,
    )
    print("ARB FOUND" if opp else "No guaranteed arb")

if __name__ == "__main__":
    main()
