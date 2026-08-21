import os
from dotenv import load_dotenv

load_dotenv()

# Alpaca API
API_KEY = os.getenv("APCA_API_KEY")
API_SECRET = os.getenv("APCA_API_SECRET")
BASE_URL = "https://paper-api.alpaca.markets"
FEED = "iex"  # Free tier; change to "sip" if on paid plan

# Data storage
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "market_data.duckdb")

# Tickers to track
TICKERS = ["TSLA", "AAPL", "NVDA", "SPY"]

# How far back to fetch on first run (years)
LOOKBACK_YEARS = 5
