import warnings
warnings.simplefilter("ignore")

import duckdb
import os
import pandas as pd
from datetime import datetime, timedelta

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("APCA_API_KEY")
API_SECRET = os.getenv("APCA_API_SECRET")

client = StockHistoricalDataClient(API_KEY, API_SECRET)

con = duckdb.connect("market_data.duckdb")

# Create table once if it doesn't exist
con.execute("""
CREATE TABLE IF NOT EXISTS stock_prices (
    symbol VARCHAR,
    trade_date DATE,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume BIGINT
)
""")

# Find latest stored date
latest = con.execute("""
    SELECT MAX(trade_date)
    FROM stock_prices
    WHERE symbol = 'AAPL'
""").fetchone()[0]

if latest is None:
    # First run: pull 5 years
    start_date = datetime.now() - timedelta(days=365 * 5)
else:
    # Only pull data after latest date
    start_date = datetime.combine(
        latest + timedelta(days=1),
        datetime.min.time()
    )

# Only request data if we're missing dates
if start_date.date() <= datetime.now().date():

    request = StockBarsRequest(
        symbol_or_symbols=["AAPL"],
        timeframe=TimeFrame.Day,
        start=start_date
    )

    bars = client.get_stock_bars(request)

    if not bars.df.empty:
        df = bars.df.reset_index()

        df = df[[
            "symbol",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]]

        df["trade_date"] = pd.to_datetime(
            df["timestamp"]
        ).dt.date

        df = df[[
            "symbol",
            "trade_date",
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]]

        # Append new rows
        con.register("new_data", df)

        con.execute("""
            INSERT INTO stock_prices
            SELECT *
            FROM new_data
        """)

        print(f"Added {len(df)} new rows.")
    else:
        print("No new market data available.")
else:
    print("Database already up to date.")

# Query section
user_date = input("Enter a date (YYYY-MM-DD): ")

result = con.execute("""
    SELECT symbol, trade_date, open, high, low, close
    FROM stock_prices
    WHERE trade_date = ?
""", [user_date]).fetchdf()

if result.empty:
    print("No data found for that date.")
else:
    print(result)