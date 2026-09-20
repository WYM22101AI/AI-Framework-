"""
Build Clean Database:
Populates family_quant.duckdb with 50 tickers of price history, FRED macro data,
and computes all 24 daily features.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from scripts.storage import init_db, upsert_generic
from scripts.fetch_50_tickers import fetch_universe_prices
from scripts.fred_fetcher import create_fred_client, fetch_all_series
from scripts.feature_engine import store_features

def main():
    print("=== BUILDING CLEAN QUANTITATIVE DATABASE (family_quant.duckdb) ===", flush=True)
    t0 = time.time()
    
    # 1. Init DB tables
    conn = init_db(config.DB_PATH)
    
    # 2. Fetch prices
    print("\n[Step 1/3] Fetching 10Y Daily Prices for 50 Tickers...", flush=True)
    fetch_universe_prices()
    
    # 3. Fetch FRED macro
    print("\n[Step 2/3] Ingesting FRED Macro Series (VIX, Fed Funds, 10Y Yield)...", flush=True)
    try:
        if config.FRED_API_KEY:
            client = create_fred_client(config.FRED_API_KEY)
            macro_df = fetch_all_series(client, config.FRED_SERIES)
            if not macro_df.empty:
                upsert_generic(conn, "macro_releases", macro_df, ["series_id", "observation_date"])
                print(f"    ... Ingested {len(macro_df):,} FRED macro records", flush=True)
    except Exception as e:
        print(f"    Macro fetch warning: {e}", flush=True)
    finally:
        conn.close()
        
    # 4. Compute 24 daily features
    print("\n[Step 3/3] Computing 24 Daily Features across all 50 Tickers...", flush=True)
    store_features()
    
    elapsed = time.time() - t0
    print(f"\n Clean Database Ready in {elapsed:.1f}s!", flush=True)

if __name__ == "__main__":
    main()
