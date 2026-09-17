"""
Seed Options Queue:
Discovers all historical and active options contracts for 2024-2026 across our universe
and populates the `options_contracts_queue` DuckDB table.

Usage:
    python scripts/seed_options_queue.py
"""
import sys, os, time, requests
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from scripts.storage import init_db

API_KEY = config.MASSIVE_API_KEY
BASE_URL = "https://api.massive.com"
RATE_LIMIT_DELAY = 12  # 5 calls/min

def discover_contracts(symbol: str, limit_per_call: int = 250) -> list:
    """Paginate and discover all contracts for an underlying ticker."""
    if not API_KEY:
        print("MASSIVE_API_KEY not set in .env", flush=True)
        return []

    contracts = []
    url = f"{BASE_URL}/v3/reference/options/contracts"
    params = {
        "underlying_ticker": symbol,
        "limit": limit_per_call,
        "apiKey": API_KEY
    }

    print(f"  {symbol}: discovering contracts from Massive API...", flush=True)

    while url:
        time.sleep(RATE_LIMIT_DELAY)
        try:
            resp = requests.get(url, params=params if url == f"{BASE_URL}/v3/reference/options/contracts" else {"apiKey": API_KEY}, timeout=30)
            if resp.status_code == 429:
                print("    Rate limited (429). Waiting 60s...", flush=True)
                time.sleep(60)
                continue
            if resp.status_code != 200:
                print(f"    API Error {resp.status_code}: {resp.text[:200]}", flush=True)
                break
            
            data = resp.json()
            batch = data.get("results", [])
            contracts.extend(batch)
            print(f"    ... fetched batch of {len(batch)} contracts (total so far: {len(contracts)})", flush=True)
            
            # Follow pagination if present
            next_url = data.get("next_url")
            if next_url:
                url = next_url
            else:
                break
                
            # Cap discovery per stock to top ~500 most relevant contracts to maintain high quality
            if len(contracts) >= 500:
                break
        except Exception as e:
            print(f"    Error discovering contracts for {symbol}: {e}", flush=True)
            break

    return contracts

def seed_queue():
    """Discover contracts for universe and seed into DuckDB queue table."""
    conn = init_db(config.DB_PATH)
    
    # Core universe + major index ETFs
    tickers = ["TSLA", "NVDA", "AMD", "AMZN", "AAPL", "MSFT", "META", "GOOG", "SPY", "QQQ"]
    
    total_seeded = 0
    print(f"=== Discovering Options Contracts across {len(tickers)} Tickers ===", flush=True)

    for sym in tickers:
        raw_contracts = discover_contracts(sym)
        if not raw_contracts:
            continue
            
        rows = []
        for c in raw_contracts:
            rows.append({
                "options_ticker": c.get("ticker"),
                "underlying_ticker": c.get("underlying_ticker", sym),
                "contract_type": c.get("contract_type"),
                "expiration_date": c.get("expiration_date"),
                "strike_price": c.get("strike_price"),
                "status": "pending"
            })
            
        if rows:
            import pandas as pd
            df = pd.DataFrame(rows)
            conn.register("_new_contracts", df)
            conn.execute("""
                INSERT OR IGNORE INTO options_contracts_queue (options_ticker, underlying_ticker, contract_type, expiration_date, strike_price, status)
                SELECT options_ticker, underlying_ticker, contract_type, expiration_date, strike_price, status
                FROM _new_contracts
            """)
            conn.unregister("_new_contracts")
            count = conn.execute(f"SELECT COUNT(*) FROM options_contracts_queue WHERE underlying_ticker = '{sym}'").fetchone()[0]
            print(f"  => {sym}: Queue now has {count} contracts queued.\n", flush=True)
            total_seeded += len(rows)

    total_queue = conn.execute("SELECT COUNT(*) FROM options_contracts_queue").fetchone()[0]
    conn.close()
    print(f"\nSeeding Complete! Total {total_queue} contracts currently in options_contracts_queue.", flush=True)

if __name__ == "__main__":
    seed_queue()
