# Arb Bot (Liquidity-Aware)

Starter scaffold for a depth-aware arbitrage engine across prediction markets.

## Run
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
python -m arb_bot.main
