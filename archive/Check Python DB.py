import duckdb
import pandas as pd
from datetime import datetime, timedelta
import alpaca_trade_api as tradeapi

# ----------------------------
# CONFIG
# ----------------------------
DB_PATH = "data/market_data.duckdb"
TABLE = "TSLA_history"
SYMBOL = "TSLA"

API_KEY = "PKNFU45ICRWFLLCFTJBB4WVJSL"
API_SECRET = "CYaE4knxNW9TqR5kNvbWTZKYYxNnoNcuiXcUc7Ajci1B"
BASE_URL = "https://paper-api.alpaca.markets"


# =========================
# CONNECT DB + API
# =========================
conn = duckdb.connect(DB_PATH)

api = tradeapi.REST(
    API_KEY,
    API_SECRET,
    BASE_URL,
    api_version="v2"
)

# =========================
# GET LAST DATE IN DB
# =========================
result = conn.execute(f"""
    SELECT MAX(timestamp)
    FROM {TABLE}
""").fetchone()

last_date = result[0]

if last_date is None:
    start_date = datetime.now() - timedelta(days=5 * 365)
else:
    start_date = pd.to_datetime(last_date) + timedelta(days=1)

end_date = datetime.now()

print(f"Fetching {SYMBOL} from {start_date.date()} to {end_date.date()}")

# =========================
# FETCH DATA (IMPORTANT FIX: feed='iex')
# =========================
bars = api.get_bars(
    SYMBOL,
    "1Day",
    start=str(start_date.date()),
    end=str(end_date.date()),
    adjustment="raw",
    feed="iex"   # IMPORTANT FIX FOR YOUR ERROR
).df

if bars.empty:
    print("No new data.")
    conn.close()
    exit()

# =========================
# CLEAN DATA
# =========================
bars = bars.reset_index()

bars["symbol"] = SYMBOL

# Ensure required columns exist
if "trade_count" not in bars.columns:
    bars["trade_count"] = None

if "vwap" not in bars.columns:
    bars["vwap"] = None

# Match EXACT DB schema (9 columns)
bars = bars[[
    "symbol",
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "trade_count",
    "vwap"
]]

# =========================
# CREATE TABLE IF NOT EXISTS
# =========================
conn.execute(f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    symbol TEXT,
    timestamp TIMESTAMP WITH TIME ZONE,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume DOUBLE,
    trade_count DOUBLE,
    vwap DOUBLE
)
""")

# =========================
# INSERT DATA
# =========================
conn.register("new_data", bars)

conn.execute(f"""
    INSERT INTO {TABLE}
    SELECT * FROM new_data
""")

# =========================
# VERIFY
# =========================
count = conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]

print(f"Inserted rows: {len(bars)}")
print(f"Total rows in DB: {count}")

conn.close()