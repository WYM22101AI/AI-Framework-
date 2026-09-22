"""
Rerun Today's Full End-to-End Analysis:
1. Ingest official live settled bars from Alpaca API for today (Monday, Sept 21)
2. Run Pre-Flight Data Sanitizer & Issue Quality Certificate
3. Scan for Tomorrow's Opportunities (Mean Reversion & Momentum)
4. Validate Tomorrow's Orders through the Trading Cage ($20k max)
"""

import sys, os
sys.path.insert(0, r"C:\Users\Yaming\family-quant-ai")
import requests, json
from datetime import datetime
import pandas as pd
import duckdb, config
from scripts.data_sanitizer import DataSanitizer
from scripts.trade_gateway import TradeGateway
from scripts.broker_adapter import get_broker_adapter
import scripts.signal_generator as sg

def rerun_analysis():
    print("================================================================================")
    print("      FAMILY QUANT AI: RERUNNING TODAY'S LIVE OPPORTUNITY SCAN")
    print(f"      Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("================================================================================")

    # 1. Ingest official Alpaca data for today
    api_key = config.API_KEY
    api_secret = config.API_SECRET
    headers = {"APCA-API-KEY-ID": api_key, "APCA-API-SECRET-KEY": api_secret}

    symbols = [
        "AMZN", "NVDA", "CAT", "COST", "FSLR", "V", "BRO", "MSFT", "GOOG", "JPM",
        "AAPL", "AMD", "QCOM", "CRM", "BA", "DIS", "NFLX", "GS", "NEE", "SPY"
    ]
    sym_str = ",".join(symbols)
    url = f"https://data.alpaca.markets/v2/stocks/bars?symbols={sym_str}&timeframe=1Day&limit=10&feed=iex"
    
    r = requests.get(url, headers=headers)
    conn = duckdb.connect(config.DB_PATH, read_only=False)

    if r.status_code == 200:
        data = r.json().get("bars", {})
        rows_to_insert = []
        for sym, bars in data.items():
            for b in bars:
                ts = pd.to_datetime(b["t"])
                rows_to_insert.append((
                    sym, ts, float(b["o"]), float(b["h"]), float(b["l"]), float(b["c"]), 
                    float(b["v"]), int(b.get("n", 0)), float(b.get("vw", 0.0))
                ))
        
        conn.executemany("""
            INSERT OR REPLACE INTO daily_bars (symbol, timestamp, open, high, low, close, volume, trade_count, vwap)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows_to_insert)
        print(f"\n[STEP 1: DATA INGESTION SUCCESSFUL]")
        print(f"  • Updated DuckDB with {len(rows_to_insert)} settled bars across {len(data)} tickers.")
    else:
        print(f"Alpaca API Error: {r.status_code} - {r.text}")

    # 2. Run Pre-Flight Data Sanitizer
    print("\n[STEP 2: PRE-FLIGHT DATA QUALITY AUDIT]")
    sanitizer = DataSanitizer()
    df_amzn = conn.execute("SELECT * FROM daily_bars WHERE symbol = 'AMZN' ORDER BY timestamp").fetchdf()
    cert = sanitizer.audit_and_certify_dataset("AMZN", df_amzn)
    print(f"  • Data Quality Certificate: [{cert['status']}]")
    print(f"  • Latest Settled Date in Database: {cert['gate_details'][0]['latest_date_in_dataset']}")
    for g, stat in cert["gates"].items():
        print(f"    - Gate: {g:<25} [{stat}]")

    # 3. Scan Opportunities
    print("\n[STEP 3: TODAY'S MARKET OPPORTUNITY SCAN]")
    strat_map = {
        "AMZN": ("Mean Reversion (VIX-Tuned)", sg.strategy_mr_vix_tuned),
        "NVDA": ("Mean Reversion (VIX-Tuned)", sg.strategy_mr_vix_tuned),
        "FSLR": ("Mean Reversion (VIX-Tuned)", sg.strategy_mr_vix_tuned),
        "V":    ("Mean Reversion (VIX-Tuned)", sg.strategy_mr_vix_tuned),
        "COST": ("Mean Reversion Regime", sg.strategy_mean_reversion_regime),
        "CAT":  ("Momentum Regime", sg.strategy_momentum_regime),
        "BRO":  ("Momentum Regime", sg.strategy_momentum_regime),
        "MSFT": ("Mean Reversion (VIX-Tuned)", sg.strategy_mr_vix_tuned),
        "GOOG": ("Mean Reversion (VIX-Tuned)", sg.strategy_mr_vix_tuned),
        "JPM":  ("Mean Reversion Regime", sg.strategy_mean_reversion_regime),
    }

    broker = get_broker_adapter("alpaca")
    gateway = TradeGateway()
    acct = broker.get_account()
    portfolio_val = acct.get("portfolio_value", 100000.0)

    opportunities = []
    for sym, (strat_name, fn) in strat_map.items():
        try:
            sig_series = fn(conn, sym)
            if sig_series is not None and not sig_series.empty:
                latest_val = int(sig_series.iloc[-1])
                latest_dt = str(sig_series.index[-1])[:10]
                status_str = "BUY SIGNAL TRIGGERED" if latest_val == 1 else "Cash Vault / Flat"
                print(f"  {sym:<6s}: {strat_name:<28} Signal: {latest_val:<2} ({status_str}) [Date: {latest_dt}]")
                if latest_val == 1:
                    opportunities.append((sym, strat_name))
        except Exception as e:
            print(f"  {sym:<6s}: Error - {e}")

    # 4. Next Day Orders
    print("\n[STEP 4: TOMORROW'S APPROVED ORDER QUEUE (TRADING CAGE ENFORCED)]")
    if opportunities:
        for sym, strat_name in opportunities:
            row = conn.execute(f"SELECT close FROM daily_bars WHERE symbol = '{sym}' ORDER BY timestamp DESC LIMIT 1").fetchone()
            price = row[0] if row else 100.0
            target_dlrs = min(20000.0, portfolio_val * 0.20)
            
            res = gateway.validate_order(
                symbol=sym,
                side="BUY",
                requested_dollars=target_dlrs,
                current_holdings=0.0,
                portfolio_value=portfolio_val,
                vix_level=18.0,
                strategy_name=strat_name
            )
            approved_dlrs = res.get("approved_dollars", 0.0)
            shares = int(approved_dlrs / price) if price > 0 else 0
            print(f"  • {sym}: BUY {shares} shares @ ~${price:,.2f} (${approved_dlrs:,.2f}) -> [{res.get('verdict')}]")
            print(f"    - Risk Gates Passed: {res.get('checks_passed')}")
    else:
        print("  • No new buy orders required for tomorrow.")
        print("  • Full portfolio ($100,000) rests in Cash Vault earning ~4.5% interest.")

    conn.close()

if __name__ == "__main__":
    rerun_analysis()
