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

# Massive (formerly Polygon) — free tier for options data
MASSIVE_API_KEY = os.getenv("MASSIVE_API_KEY")

# Data storage
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "family_quant.duckdb")

# Tickers to track
# Full S&P 500 universe across all 11 GICS sectors + major sector ETFs
try:
    from scripts.fetch_sp500_universe import get_all_sp500_tickers
    TICKERS = get_all_sp500_tickers()
except Exception:
    # Fallback core list
    TICKERS = [
        "TSLA", "AAPL", "NVDA", "MSFT", "META", "AMZN", "GOOG", "AMD",
        "JPM", "GS", "MS", "BAC", "V", "MA", "BLK",
        "JNJ", "UNH", "LLY", "PFE", "ABBV", "MRK",
        "HD", "NKE", "MCD", "SBUX", "TGT", "WMT", "COST", "PG", "KO",
        "XOM", "CVX", "COP", "CAT", "GE", "BA", "UNP", "HON",
        "DIS", "NFLX", "NEE", "PLD", "LIN",
        "SPY", "QQQ", "IWM", "DIA"
    ]

# How far back to fetch on first run (years)
LOOKBACK_YEARS = 10
