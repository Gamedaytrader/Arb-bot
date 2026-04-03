import os
from dotenv import load_dotenv
 
load_dotenv()
 
KALSHI_API_KEY: str = os.getenv("KALSHI_API_KEY", "")
KALSHI_API_SECRET: str = os.getenv("KALSHI_API_SECRET", "")
NOVIG_OAUTH_TOKEN: str = os.getenv("NOVIG_OAUTH_TOKEN", "")
DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "")
 
MIN_EDGE: float = float(os.getenv("MIN_EDGE", "0.04"))
MAX_BET_SIZE: float = float(os.getenv("MAX_BET_SIZE", "100"))
POLL_INTERVAL: int = int(os.getenv("POLL_INTERVAL", "10"))
DRY_RUN: bool = os.getenv("DRY_RUN", "true").lower() == "true"
MIN_LIQUIDITY_USD: float = float(os.getenv("MIN_LIQUIDITY_USD", "50"))
MATCH_THRESHOLD: float = float(os.getenv("MATCH_THRESHOLD", "85"))
 
KALSHI_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
NOVIG_GQL_URL = "https://gql.novig.us/v1/graphql"
POLYMARKET_GAMMA_URL = "https://gamma-api.polymarket.com"
POLYMARKET_CLOB_URL = "https://clob.polymarket.com"
