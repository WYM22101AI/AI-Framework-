"""
Check Options Crawler Status:
Reports queue completion, rows in options_activity, and background worker status.

Usage:
    python scripts/check_crawler_status.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import duckdb, config
import pandas as pd

def check_status():
    progress_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "crawler_progress.txt")
    if os.path.exists(progress_file):
        with open(progress_file) as f:
            print(f.read())
            print()
            
    conn = duckdb.connect(config.DB_PATH, read_only=True)
    
    # Check queue table
    try:
        q_summary = conn.execute("""
            SELECT 
                underlying_ticker,
                COUNT(*) as total_contracts,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(bars_count) as total_bars
            FROM options_contracts_queue
            GROUP BY underlying_ticker
            ORDER BY underlying_ticker
        """).fetchdf()
        
        print("--- Contract Queue Breakdown by Stock ---")
        print(q_summary.to_string(index=False))
    except Exception as e:
        print(f"Queue not initialized yet: {e}")

    # Check options_activity table
    try:
        act_summary = conn.execute("""
            SELECT 
                symbol,
                COUNT(*) as daily_records,
                MIN(date) as earliest_date,
                MAX(date) as latest_date,
                ROUND(AVG(total_options_volume), 0) as avg_daily_vol
            FROM options_activity
            GROUP BY symbol
            ORDER BY symbol
        """).fetchdf()
        
        print("\n--- Options Activity Daily Table Summary ---")
        print(act_summary.to_string(index=False))
    except Exception as e:
        print(f"Options activity table empty or error: {e}")

    conn.close()

if __name__ == "__main__":
    check_status()
