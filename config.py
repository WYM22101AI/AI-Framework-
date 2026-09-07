import os
from dotenv import load_dotenv

load_dotenv()

# Alpaca API
API_KEY = os.getenv("APCA_API_KEY")
API_SECRET = os.getenv("APCA_API_SECRET")
BASE_URL = "https://paper-api.alpaca.markets"
FEED = "iex"  # Free tier; change to "sip" if on paid plan

# FRED API
FRED_API_KEY = os.getenv("FRED_API_KEY")
FRED_SERIES = [
    "CPIAUCSL",      # CPI (inflation)
    "UNRATE",        # Unemployment rate
    "FEDFUNDS",      # Federal funds rate
    "DGS10",         # 10-Year Treasury yield
    "GDP",           # GDP
    "RSAFS",         # Retail sales
    "UMCSENT",       # Consumer sentiment
    "VIXCLS",        # VIX
]

# Alpha Vantage
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

# SEC EDGAR (no key needed, just User-Agent)
SEC_USER_AGENT = "FamilyQuantAI yamingwang@gmail.com"

# Data storage
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "market_data.duckdb")

# Tickers to track
# Core universe: liquid, high-volume stocks across sectors + SPY benchmark
TICKERS = [
    # Tech
    "TSLA", "AAPL", "NVDA", "MSFT", "META", "AMZN", "GOOG", "AMD",
    # Finance
    "JPM", "GS",
    # Healthcare
    "JNJ", "UNH",
    # Consumer
    "WMT", "HD",
    # Energy
    "XOM",
    # Index ETFs (benchmarks + tradeable)
    "SPY",   # S&P 500
    "QQQ",   # Nasdaq 100
    "IWM",   # Russell 2000 (small cap)
    "DIA",   # Dow Jones
]

# How far back to fetch on first run (years)
LOOKBACK_YEARS = 10
