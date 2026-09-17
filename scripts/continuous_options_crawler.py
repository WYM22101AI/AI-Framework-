"""
Continuous Options Crawler Worker:
Consumes pending contracts from `options_contracts_queue`, fetches 2-year daily bars,
aggregates daily call/put volume into `options_activity`, and updates checkpoint status.

Resilient Design:
- Safe 12-13s sleep per request (5 calls/min limit).
- Checkpoints progress after every single contract in DuckDB.
- If interrupted, immediately resumes at the next pending contract.
- Writes progress to `data/crawler_progress.txt`.

Usage:
    python scripts/continuous_options_crawler.py
"""
import sys, os, time, requests, json
from datetime import datetime, timezone, timedelta
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from scripts.storage import init_db

API_KEY = config.MASSIVE_API_KEY
BASE_URL = "https://api.massive.com"
RATE_LIMIT_DELAY = 12.5  # safe 12.5s pacing (4.8 calls/min)

PROGRESS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "crawler_progress.txt")

def update_progress_file(symbol, current, total, completed_count, remaining, bars_total):
    """Write human-readable status to data/crawler_progress.txt."""
    pct = (completed_count / total * 100) if total > 0 else 0
    eta_mins = (remaining * RATE_LIMIT_DELAY) / 60
    eta_hours = eta_mins / 60
    
    lines = [
        "===========================================================",
        f"  CONTINUOUS OPTIONS CRAWLER: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "===========================================================",
        f"Status:            RUNNING (Active background worker)",
        f"Current Contract:  {current}",
        f"Current Stock:     {symbol}",
        f"Overall Progress:  {completed_count:,} / {total:,} ({pct:.1f}%)",
        f"Remaining:         {remaining:,} contracts",
        f"Total Bars Stored: {bars_total:,} daily contract records",
        f"Estimated Time:    ~{eta_hours:.1f} hours ({eta_mins:.0f} minutes)",
        "Checkpointing:     DuckDB options_contracts_queue (Resilient)",
        "Rate Limit Pacing: 12.5s / call (Free tier safe)",
        "==========================================================="
    ]
    with open(PROGRESS_FILE, "w") as f:
        f.write("\n".join(lines))

def fetch_contract_bars(options_ticker: str, from_date: str, to_date: str) -> list:
    """Fetch daily bars for one options contract."""
    url = f"{BASE_URL}/v2/aggs/ticker/{options_ticker}/range/1/day/{from_date}/{to_date}"
    params = {"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": API_KEY}
    
    time.sleep(RATE_LIMIT_DELAY)
    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 429:
            print(f"  [429 Rate Limit] Pausing 60s...", flush=True)
            time.sleep(60)
            resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            return resp.json().get("results", [])
        else:
            print(f"  API status {resp.status_code} for {options_ticker}", flush=True)
            return []
    except Exception as e:
        print(f"  Request error for {options_ticker}: {e}", flush=True)
        return []

def run_crawler():
    if not API_KEY:
        print("MASSIVE_API_KEY not set in .env", flush=True)
        return

    from_date = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")
    to_date = datetime.now().strftime("%Y-%m-%d")

    print(f"Starting Continuous Options Historical Crawler ({from_date} to {to_date})...", flush=True)

    while True:
        conn = init_db(config.DB_PATH)
        
        # Get counts
        total = conn.execute("SELECT COUNT(*) FROM options_contracts_queue").fetchone()[0]
        completed = conn.execute("SELECT COUNT(*) FROM options_contracts_queue WHERE status = 'completed'").fetchone()[0]
        
        # Fetch next batch of pending contracts
        pending_batch = conn.execute("""
            SELECT options_ticker, underlying_ticker, contract_type
            FROM options_contracts_queue
            WHERE status = 'pending'
            ORDER BY underlying_ticker, expiration_date DESC
            LIMIT 50
        """).fetchall()
        
        conn.close()

        if not pending_batch:
            print("\nAll contracts in queue have been processed! Crawler complete.", flush=True)
            with open(PROGRESS_FILE, "w") as f:
                f.write(f"CRAWLER FINISHED at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}. Total {total} contracts processed.")
            break

        for contract_tuple in pending_batch:
            opt_ticker, symbol, contract_type = contract_tuple
            
            bars = fetch_contract_bars(opt_ticker, from_date, to_date)
            
            conn = init_db(config.DB_PATH)
            
            if bars:
                # Aggregate bars into options_activity
                for b in bars:
                    ts = b.get("t", 0)
                    dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
                    vol = b.get("v", 0)
                    call_vol = vol if contract_type == "call" else 0
                    put_vol = vol if contract_type == "put" else 0

                    conn.execute("""
                        INSERT INTO options_activity (symbol, date, total_options_volume, call_volume, put_volume, put_call_ratio, n_contracts_sampled)
                        VALUES (?, ?, ?, ?, ?, NULL, 1)
                        ON CONFLICT (symbol, date) DO UPDATE SET
                            total_options_volume = options_activity.total_options_volume + EXCLUDED.total_options_volume,
                            call_volume = options_activity.call_volume + EXCLUDED.call_volume,
                            put_volume = options_activity.put_volume + EXCLUDED.put_volume,
                            put_call_ratio = CASE 
                                WHEN (options_activity.call_volume + EXCLUDED.call_volume) > 0 
                                THEN (options_activity.put_volume + EXCLUDED.put_volume)::DOUBLE / (options_activity.call_volume + EXCLUDED.call_volume)
                                ELSE NULL 
                            END,
                            n_contracts_sampled = options_activity.n_contracts_sampled + 1
                    """, [symbol, dt, vol, call_vol, put_vol])
                
                status = "completed"
            else:
                status = "empty" # Contract had no trades in the 2-year window

            # Checkpoint contract
            conn.execute("""
                UPDATE options_contracts_queue
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP, bars_count = ?
                WHERE options_ticker = ?
            """, [len(bars), opt_ticker])

            # Refresh progress numbers
            completed += 1
            remaining = total - completed
            bars_total = conn.execute("SELECT COALESCE(SUM(bars_count), 0) FROM options_contracts_queue WHERE status = 'completed'").fetchone()[0]
            
            conn.close()

            print(f"[{completed}/{total}] {opt_ticker} ({len(bars)} bars) -> {status}", flush=True)
            update_progress_file(symbol, opt_ticker, total, completed, remaining, bars_total)

if __name__ == "__main__":
    run_crawler()
