"""
Main pipeline: fetch latest market data from Alpaca and store in DuckDB.
Run this script manually or via scheduled task (scripts/run_update.bat).
"""

import sys
import os
from datetime import datetime, timedelta

import pandas as pd

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from scripts.market_fetcher import create_client, fetch_bars
from scripts.storage import init_db, get_last_date, upsert_bars, get_row_counts


def main():
    print(f"=== Market Data Update: {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    print(f"Tickers: {config.TICKERS}")
    print(f"DB: {config.DB_PATH}")
    print()

    # Validate credentials
    if not config.API_KEY or not config.API_SECRET:
        print("ERROR: APCA_API_KEY and APCA_API_SECRET must be set in .env")
        sys.exit(1)

    # Initialize
    conn = init_db(config.DB_PATH)
    client = create_client(config.API_KEY, config.API_SECRET, config.BASE_URL)

    # Determine date range: use the oldest "last date" across all tickers
    end_date = datetime.now()
    start_date = end_date  # will be adjusted below

    for symbol in config.TICKERS:
        last = get_last_date(conn, symbol)
        if last is None:
            symbol_start = end_date - timedelta(days=config.LOOKBACK_YEARS * 365)
        else:
            # Strip timezone from stored timestamp for comparison
            last_naive = pd.Timestamp(last).tz_localize(None).to_pydatetime()
            symbol_start = last_naive + timedelta(days=1)

        if symbol_start < start_date:
            start_date = symbol_start

    if start_date.date() >= end_date.date():
        print("All tickers are up to date. Nothing to fetch.")
        conn.close()
        return

    print(f"Fetching data from {start_date.date()} to {end_date.date()}...")

    # Fetch
    df = fetch_bars(client, config.TICKERS, start_date, end_date, feed=config.FEED)

    if df.empty:
        print("No new data returned from Alpaca.")
        conn.close()
        return

    # Store
    rows_inserted = upsert_bars(conn, df)
    print(f"Inserted/updated {rows_inserted} rows.")

    # Summary
    print("\nRow counts per ticker:")
    counts = get_row_counts(conn)
    for symbol, count in counts.items():
        print(f"  {symbol}: {count:,} rows")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
