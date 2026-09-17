import sys, os, time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from scripts.market_fetcher import create_client, fetch_bars
from scripts.storage import init_db, upsert_bars, get_last_date

def fetch_universe_prices():
    print(f"=== Ingesting Historical Price Bars for {len(config.TICKERS)} Tickers ===", flush=True)
    
    conn = init_db(config.DB_PATH)
    client = create_client(config.API_KEY, config.API_SECRET, config.BASE_URL)
    
    end_date = datetime.now()
    lookback = config.LOOKBACK_YEARS * 365
    
    total_new_bars = 0
    
    for i, symbol in enumerate(config.TICKERS):
        last = get_last_date(conn, symbol)
        if last is None:
            start_date = end_date - timedelta(days=lookback)
            mode = "FULL 10Y BACKFILL"
        else:
            import pandas as pd
            last_naive = pd.Timestamp(last).tz_localize(None).to_pydatetime()
            start_date = last_naive + timedelta(days=1)
            mode = "INCREMENTAL"
            
        if start_date.date() >= end_date.date():
            print(f"[{i+1}/{len(config.TICKERS)}] {symbol}: already up to date.", flush=True)
            continue
            
        print(f"[{i+1}/{len(config.TICKERS)}] {symbol} ({mode} from {start_date.strftime('%Y-%m-%d')}): fetching...", flush=True)
        
        try:
            df = fetch_bars(client, [symbol], start_date, end_date, feed=config.FEED)
            if not df.empty:
                rows = upsert_bars(conn, df)
                total_new_bars += rows
                print(f"    ... {symbol}: {rows:,} bars stored", flush=True)
            else:
                print(f"    ... {symbol}: no bars returned", flush=True)
        except Exception as e:
            print(f"    ... {symbol}: ERROR: {e}", flush=True)
            
        time.sleep(0.5) # gentle pacing for Alpaca API

    total_bars = conn.execute("SELECT COUNT(*) FROM daily_bars").fetchone()[0]
    total_symbols = conn.execute("SELECT COUNT(DISTINCT symbol) FROM daily_bars").fetchone()[0]
    conn.close()
    
    print(f"\nPrice Ingestion Complete! Stored {total_new_bars:,} new bars.", flush=True)
    print(f"Database now holds {total_bars:,} bars across {total_symbols} unique symbols.", flush=True)

if __name__ == "__main__":
    fetch_universe_prices()
