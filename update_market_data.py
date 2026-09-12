"""
Main pipeline: fetch market data from multiple sources and store in DuckDB.
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
from scripts.storage import init_db, get_last_date, upsert_bars, upsert_generic, get_all_table_counts


def fetch_stock_prices(conn, client):
    """Fetch daily stock bars from Alpaca."""
    print("[1/7] Stock prices (Alpaca)...")

    end_date = datetime.now()
    start_date = end_date

    for symbol in config.TICKERS:
        last = get_last_date(conn, symbol)
        if last is None:
            symbol_start = end_date - timedelta(days=config.LOOKBACK_YEARS * 365)
        else:
            last_naive = pd.Timestamp(last).tz_localize(None).to_pydatetime()
            symbol_start = last_naive + timedelta(days=1)

        if symbol_start < start_date:
            start_date = symbol_start

    if start_date.date() >= end_date.date():
        print("  Prices: already up to date.")
        return

    df = fetch_bars(client, config.TICKERS, start_date, end_date, feed=config.FEED)
    if not df.empty:
        rows = upsert_bars(conn, df)
        print(f"  Prices: {rows} rows inserted/updated.")
    else:
        print("  Prices: no new data.")


def fetch_macro_data(conn):
    """Fetch FRED macro economic data."""
    print("[2/7] Macro data (FRED)...")

    if not config.FRED_API_KEY:
        print("  Skipped: FRED_API_KEY not set in .env")
        return

    from scripts.fred_fetcher import create_fred_client, fetch_all_series

    client = create_fred_client(config.FRED_API_KEY)
    df = fetch_all_series(client, config.FRED_SERIES)

    if not df.empty:
        rows = upsert_generic(conn, "macro_releases", df, ["series_id", "observation_date"])
        print(f"  Macro: {rows} total observations stored.")


def fetch_earnings_data(conn):
    """Fetch earnings from Alpha Vantage."""
    print("[3/7] Earnings (Alpha Vantage)...")

    if not config.ALPHA_VANTAGE_API_KEY:
        print("  Skipped: ALPHA_VANTAGE_API_KEY not set in .env")
        return

    from scripts.earnings_fetcher import fetch_all_earnings

    df = fetch_all_earnings(config.ALPHA_VANTAGE_API_KEY, config.TICKERS)

    if not df.empty:
        rows = upsert_generic(conn, "earnings", df, ["symbol", "fiscal_date_ending"])
        print(f"  Earnings: {rows} quarters stored.")


def fetch_sec_data(conn):
    """Fetch SEC EDGAR fundamentals."""
    print("[4/7] Fundamentals (SEC EDGAR)...")

    from scripts.sec_fetcher import fetch_all_fundamentals

    df = fetch_all_fundamentals(config.TICKERS, config.SEC_USER_AGENT)

    if not df.empty:
        rows = upsert_generic(conn, "fundamentals", df, ["symbol", "fiscal_date_ending"])
        print(f"  SEC: {rows} filings stored.")


def fetch_options_data(conn, client):
    """Fetch options snapshots from Alpaca (using alpaca-py)."""
    print("[5/7] Options (Alpaca)...")

    from scripts.options_fetcher import fetch_all_options

    try:
        # Get latest prices to determine ATM strikes
        spot_prices = {}
        for symbol in config.TICKERS:
            if symbol == "SPY":
                continue
            try:
                trade = client.get_latest_trade(symbol)
                spot_prices[symbol] = trade.price
            except Exception:
                pass

        df = fetch_all_options(config.API_KEY, config.API_SECRET, config.TICKERS, spot_prices)
        if not df.empty:
            rows = upsert_generic(conn, "options_snapshot", df, ["symbol", "snapshot_date"])
            print(f"  Options: {rows} snapshots stored.")
        else:
            print("  Options: no data returned.")
    except Exception as e:
        print(f"  Options: SKIPPED - {e}")


def fetch_news_data(conn, client):
    """Fetch news from Alpaca."""
    print("[6/7] News (Alpaca)...")

    from scripts.news_fetcher import fetch_news

    try:
        df = fetch_news(client, config.TICKERS, days_back=7)
        if not df.empty:
            rows = upsert_generic(conn, "news", df, ["id", "symbol"])
            print(f"  News: {rows} articles stored.")
        else:
            print("  News: no articles found.")
    except Exception as e:
        print(f"  News: SKIPPED - {e}")


def fetch_massive_options(conn):
    """Fetch options activity from Massive (Polygon) — free tier."""
    print("[7/7] Options activity (Massive)...")

    if not config.MASSIVE_API_KEY:
        print("  Skipped: MASSIVE_API_KEY not set in .env")
        return

    from scripts.massive_options import fetch_all_tickers
    fetch_all_tickers(days_back=7)  # Fetch last week of data


def main():
    print(f"=== Market Data Update: {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    print(f"Tickers: {config.TICKERS}")
    print(f"DB: {config.DB_PATH}")
    print()

    # Validate Alpaca credentials
    if not config.API_KEY or not config.API_SECRET:
        print("ERROR: APCA_API_KEY and APCA_API_SECRET must be set in .env")
        sys.exit(1)

    # Initialize DB and Alpaca client
    conn = init_db(config.DB_PATH)
    client = create_client(config.API_KEY, config.API_SECRET, config.BASE_URL)

    # Run all fetchers (each handles its own errors)
    fetch_stock_prices(conn, client)

    try:
        fetch_macro_data(conn)
    except Exception as e:
        print(f"  Macro: FAILED - {e}")

    try:
        fetch_earnings_data(conn)
    except Exception as e:
        print(f"  Earnings: FAILED - {e}")

    try:
        fetch_sec_data(conn)
    except Exception as e:
        print(f"  SEC: FAILED - {e}")

    try:
        fetch_options_data(conn, client)
    except Exception as e:
        print(f"  Options: FAILED - {e}")

    try:
        fetch_news_data(conn, client)
    except Exception as e:
        print(f"  News: FAILED - {e}")

    # Massive (Polygon) options activity
    try:
        fetch_massive_options(conn)
    except Exception as e:
        print(f"  Massive Options: FAILED - {e}")

    # Summary
    print("\n=== Database Summary ===")
    counts = get_all_table_counts(conn)
    for table, count in counts.items():
        print(f"  {table}: {count:,} rows")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
