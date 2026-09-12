"""
Massive (Polygon) Options Fetcher: fetch daily options activity per underlying stock.

Strategy: For each ticker, we aggregate options volume across all contracts
to detect unusual activity. On the free tier (5 calls/min, 2yr history),
we use the All Contracts + Custom Bars endpoints.

Approach for unusual activity detection:
1. Use All Contracts to find active options for each stock
2. Use Custom Bars to get daily volume per contract
3. Aggregate into: total_volume, call_volume, put_volume, put_call_ratio

Usage:
    python scripts/massive_options.py           # Fetch latest 30 days
    python scripts/massive_options.py --backfill # Fetch full 2-year history
"""

import sys
import os
import time
import requests
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from scripts.storage import init_db

API_KEY = config.MASSIVE_API_KEY
BASE_URL = "https://api.massive.com"
RATE_LIMIT_DELAY = 13  # 5 calls/min = 1 call per 12s, add buffer


def _api_get(endpoint: str, params: dict = None) -> dict:
    """Make a rate-limited API call to Massive."""
    if not API_KEY:
        print("  WARNING: MASSIVE_API_KEY not set. Skipping options fetch.")
        return {}

    url = f"{BASE_URL}{endpoint}"
    if params is None:
        params = {}
    params["apiKey"] = API_KEY

    time.sleep(RATE_LIMIT_DELAY)
    resp = requests.get(url, params=params, timeout=30)

    if resp.status_code == 429:
        print("  Rate limited. Waiting 60s...")
        time.sleep(60)
        resp = requests.get(url, params=params, timeout=30)

    if resp.status_code != 200:
        print(f"  API error {resp.status_code}: {resp.text[:200]}")
        return {}

    return resp.json()


def get_active_contracts(symbol: str, limit: int = 100) -> list:
    """Get currently active options contracts for a stock."""
    data = _api_get("/v3/reference/options/contracts", {
        "underlying_ticker": symbol,
        "expired": "false",
        "limit": limit,
        "order": "desc",
        "sort": "open_interest",
    })
    return data.get("results", [])


def get_contract_daily_bars(options_ticker: str, from_date: str, to_date: str) -> list:
    """Get daily OHLC bars for a single options contract."""
    data = _api_get(
        f"/v2/aggs/ticker/{options_ticker}/range/1/day/{from_date}/{to_date}",
        {"adjusted": "true", "sort": "asc", "limit": 50000}
    )
    return data.get("results", [])


def fetch_options_activity(symbol: str, from_date: str, to_date: str,
                           max_contracts: int = 20) -> pd.DataFrame:
    """
    Fetch daily aggregated options activity for a stock.
    Gets the top contracts by OI, then sums daily volume.

    Returns DataFrame with: date, symbol, total_volume, call_volume, put_volume,
    put_call_ratio, n_contracts_sampled
    """
    print(f"  {symbol}: finding active contracts...")
    contracts = get_active_contracts(symbol, limit=max_contracts)

    if not contracts:
        print(f"  {symbol}: no contracts found")
        return pd.DataFrame()

    print(f"  {symbol}: fetching bars for {len(contracts)} contracts (this takes ~{len(contracts)*RATE_LIMIT_DELAY}s)...")

    daily_data = {}  # date -> {call_vol, put_vol}

    for i, contract in enumerate(contracts):
        ticker = contract.get("ticker", "")
        contract_type = contract.get("contract_type", "unknown")

        bars = get_contract_daily_bars(ticker, from_date, to_date)

        for bar in bars:
            ts = bar.get("t", 0)
            date_str = datetime.utcfromtimestamp(ts / 1000).strftime("%Y-%m-%d")
            vol = bar.get("v", 0)

            if date_str not in daily_data:
                daily_data[date_str] = {"call_volume": 0, "put_volume": 0}

            if contract_type == "call":
                daily_data[date_str]["call_volume"] += vol
            elif contract_type == "put":
                daily_data[date_str]["put_volume"] += vol

        if (i + 1) % 5 == 0:
            print(f"    ... {i+1}/{len(contracts)} contracts processed")

    if not daily_data:
        return pd.DataFrame()

    rows = []
    for date_str, vols in sorted(daily_data.items()):
        call_v = vols["call_volume"]
        put_v = vols["put_volume"]
        total = call_v + put_v
        pc_ratio = put_v / call_v if call_v > 0 else None

        rows.append({
            "symbol": symbol,
            "date": date_str,
            "total_options_volume": total,
            "call_volume": call_v,
            "put_volume": put_v,
            "put_call_ratio": pc_ratio,
            "n_contracts_sampled": len(contracts),
        })

    return pd.DataFrame(rows)


def fetch_all_tickers(days_back: int = 30, max_contracts_per_ticker: int = 20):
    """Fetch options activity for all tickers in config."""
    if not API_KEY:
        print("MASSIVE_API_KEY not set in .env. Get a free key at https://massive.com/dashboard")
        return

    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    print(f"Fetching options activity from Massive (Polygon)")
    print(f"  Date range: {from_date} to {to_date}")
    print(f"  Tickers: {len(config.TICKERS)}")
    print(f"  Rate limit: {RATE_LIMIT_DELAY}s per call (free tier)")

    # Skip index ETFs that have too many contracts
    skip_tickers = {"SPY"}  # SPY has thousands of contracts, skip for now
    tickers = [t for t in config.TICKERS if t not in skip_tickers]

    conn = init_db(config.DB_PATH)
    total_rows = 0

    for symbol in tickers:
        try:
            df = fetch_options_activity(symbol, from_date, to_date, max_contracts_per_ticker)
            if not df.empty:
                conn.register("_opt_data", df)
                conn.execute("""
                    DELETE FROM options_activity
                    WHERE EXISTS (
                        SELECT 1 FROM _opt_data
                        WHERE options_activity.symbol = _opt_data.symbol
                        AND options_activity.date = _opt_data.date
                    )
                """)
                conn.execute("INSERT INTO options_activity SELECT symbol, date, total_options_volume, call_volume, put_volume, put_call_ratio, n_contracts_sampled FROM _opt_data")
                conn.unregister("_opt_data")
                total_rows += len(df)
                print(f"  {symbol}: stored {len(df)} rows")
            else:
                print(f"  {symbol}: no data")
        except Exception as e:
            print(f"  {symbol}: ERROR - {e}")

    conn.close()
    print(f"\nDone. Total: {total_rows} rows stored in options_activity table.")


if __name__ == "__main__":
    backfill = "--backfill" in sys.argv
    days = 730 if backfill else 30  # 2 years for backfill
    fetch_all_tickers(days_back=days)
