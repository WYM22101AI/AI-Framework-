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
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "market_data.duckdb")

# Tickers to track
# Core universe: liquid, high-volume stocks across sectors + SPY benchmark
TICKERS = [
    # 1. Technology & Semiconductors (11)
    "TSLA", "AAPL", "NVDA", "MSFT", "META", "AMZN", "GOOG", "AMD", "AVGO", "QCOM", "INTC",
    # 2. Financials (7)
    "JPM", "GS", "MS", "BAC", "V", "MA", "BLK",
    # 3. Healthcare & Biotech (6)
    "JNJ", "UNH", "LLY", "PFE", "ABBV", "MRK",
    # 4. Consumer Discretionary & Retail (5)
    "HD", "NKE", "MCD", "SBUX", "TGT",
    # 5. Consumer Staples (4)
    "WMT", "COST", "PG", "KO",
    # 6. Energy (3)
    "XOM", "CVX", "COP",
    # 7. Industrials & Aerospace (5)
    "CAT", "GE", "BA", "UNP", "HON",
    # 8. Communication Services (2)
    "DIS", "NFLX",
    # 9. Utilities & Real Estate (2)
    "NEE", "PLD",
    # 10. Materials (1)
    "LIN",
    # 11. Index & Sector Benchmark ETFs (4)
    "SPY",   # S&P 500 Benchmark
    "QQQ",   # Nasdaq 100
    "IWM",   # Russell 2000 Small Caps
    "DIA",   # Dow Jones Industrial Average
]

# How far back to fetch on first run (years)
LOOKBACK_YEARS = 10
