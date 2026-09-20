"""
Market-Day Aware Automated Execution Runner
1. Verifies if today is a US market trading day (excludes weekends & NYSE holidays).
2. Fetches today's closing prices.
3. Runs the Daily Executive Monitor and executes approved paper trades.
4. Generates daily performance report.
"""

import sys, os
from datetime import datetime, date
import holidays

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from scripts.daily_monitor import generate_daily_executive_report

def is_market_open_today() -> bool:
    today = date.today()
    # Check weekend (5 = Saturday, 6 = Sunday)
    if today.weekday() >= 5:
        return False
    
    # Check US NYSE holidays
    us_holidays = holidays.US(years=today.year)
    if today in us_holidays:
        return False
    
    # Specific NYSE closures (e.g. Good Friday)
    nyse_holidays = holidays.NYSE(years=today.year) if hasattr(holidays, 'NYSE') else us_holidays
    if today in nyse_holidays:
        return False
        
    return True

def run_cycle():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"=== FAMILY QUANT DAILY TRADING CYCLE ({now_str}) ===", flush=True)
    
    try:
        is_open = is_market_open_today()
    except Exception:
        # Fallback to weekday check if holidays package not present
        is_open = date.today().weekday() < 5

    if not is_open:
        print(f"Today ({date.today()}) is a weekend or NYSE market holiday. Market is CLOSED. Skipping execution.", flush=True)
        return

    print("Market is OPEN today. Running daily ingestion and executive trading monitor...", flush=True)

    # 1. Ingest today's bars (optional fetcher step)
    try:
        from scripts.fetcher import fetch_all_daily_bars
        print("Fetching latest daily price bars...", flush=True)
        fetch_all_daily_bars(tickers=config.TICKERS[:50], lookback_days=5)
    except Exception as e:
        print(f"Fetcher note: {e}", flush=True)

    # 2. Run Executive Trading Monitor & Paper Order Submission
    print("\nExecuting Daily Executive Monitor & Paper Trader...", flush=True)
    generate_daily_executive_report(execute_orders=True, broker_name="alpaca")
    print("\nDaily trading cycle completed successfully.", flush=True)

if __name__ == "__main__":
    run_cycle()
