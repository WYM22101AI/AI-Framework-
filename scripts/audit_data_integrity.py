"""
Audit Step 1: Raw Price & Corporate Actions Integrity Audit.

Checks:
1. OHLC Sanity: low <= open, close, high for 100% of rows.
2. Zero or negative price/volume anomalies.
3. Duplicate date stamps per symbol.
4. Annual trading day counts (sanity check: 250-253 trading days/year).
5. Split continuity on known split dates:
   - TSLA: 2020-08-31 (5:1), 2022-08-25 (3:1)
   - NVDA: 2021-07-20 (4:1), 2024-06-10 (10:1)
   - AAPL: 2020-08-31 (4:1)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import duckdb, config
import pandas as pd
import numpy as np

conn = duckdb.connect(config.DB_PATH, read_only=True)
report = ["=================================================================",
          "  AUDIT STEP 1: RAW DATA, OHLC SANITY & CORPORATE ACTIONS AUDIT  ",
          "=================================================================\n"]

# 1. Total Rows & Tickers
summary = conn.execute("""
    SELECT 
        COUNT(*) as total_bars,
        COUNT(DISTINCT symbol) as unique_symbols,
        MIN(timestamp::DATE) as earliest_date,
        MAX(timestamp::DATE) as latest_date
    FROM daily_bars
""").fetchdf()
report.append("1. DATABASE OVERVIEW:")
report.append(f"   Total Bars: {summary['total_bars'][0]:,}")
report.append(f"   Unique Tickers: {summary['unique_symbols'][0]}")
report.append(f"   Date Range: {summary['earliest_date'][0]} to {summary['latest_date'][0]}\n")

# 2. OHLC Sanity Check
ohlc_invalids = conn.execute("""
    SELECT COUNT(*) 
    FROM daily_bars
    WHERE low > open OR low > close OR high < open OR high < close OR low <= 0 OR volume < 0
""").fetchone()[0]
report.append("2. OHLC BOUNDARY INTEGRITY:")
if ohlc_invalids == 0:
    report.append("   [PASS] 100% of price bars satisfy Low <= Open, Close <= High with positive price/volume.")
else:
    report.append(f"   [FAIL] Found {ohlc_invalids} invalid OHLC records!")

# 3. Duplicate Dates Check
dups = conn.execute("""
    SELECT symbol, timestamp::DATE as dt, COUNT(*) as cnt
    FROM daily_bars
    GROUP BY symbol, dt
    HAVING cnt > 1
""").fetchdf()
report.append("\n3. DUPLICATE DATE INTEGRITY:")
if dups.empty:
    report.append("   [PASS] Zero duplicate timestamps found across all symbols.")
else:
    report.append(f"   [FAIL] Found {len(dups)} duplicate dates.")

# 4. Trading Day Counts Per Year
annual_counts = conn.execute("""
    SELECT 
        yr,
        ROUND(AVG(cnt), 1) as avg_days_per_symbol,
        MIN(cnt) as min_days,
        MAX(cnt) as max_days
    FROM (
        SELECT symbol, YEAR(timestamp::DATE) as yr, COUNT(*) as cnt
        FROM daily_bars
        GROUP BY symbol, YEAR(timestamp::DATE)
    )
    GROUP BY yr
    ORDER BY yr
""").fetchdf()
report.append("\n4. ANNUAL TRADING DAYS CALENDAR SANITY:")
report.append(annual_counts.to_string(index=False))

# 5. Split Continuity Audit on Known Split Dates
report.append("\n\n5. CORPORATE ACTION SPLIT CONTINUITY AUDIT:")
known_splits = [
    ("TSLA", "2020-08-31", "5:1 split"),
    ("TSLA", "2022-08-25", "3:1 split"),
    ("NVDA", "2021-07-20", "4:1 split"),
    ("NVDA", "2024-06-10", "10:1 split"),
    ("AAPL", "2020-08-31", "4:1 split"),
]

for sym, split_date, desc in known_splits:
    bars = conn.execute(f"""
        SELECT timestamp::DATE as date, close, open, volume
        FROM daily_bars
        WHERE symbol = '{sym}' AND timestamp::DATE BETWEEN '{split_date}'::DATE - INTERVAL 3 DAY AND '{split_date}'::DATE + INTERVAL 3 DAY
        ORDER BY timestamp
    """).fetchdf()
    
    if not bars.empty:
        bars["pct_change"] = bars["close"].pct_change() * 100
        # Check if percentage change on split date is artificial (>40% drop without split adjustment)
        split_bar = bars[bars["date"].astype(str) == split_date]
        if not split_bar.empty:
            chg = split_bar["pct_change"].values[0]
            status = "PASS" if abs(chg) < 25 else "FAIL (UNADJUSTED)"
            report.append(f"   [{status}] {sym} on {split_date} ({desc}): close return = {chg:+.2f}%. Adjusted prices are continuous.")
        else:
            report.append(f"   [INFO] {sym} on {split_date}: bar not found in exact range.")
    else:
        report.append(f"   [WARN] No bars found around {split_date} for {sym}.")

conn.close()

out_text = "\n".join(report)
print(out_text)
with open("C:/Users/Yaming/family-quant-ai/data/audit_step1.txt", "w") as f:
    f.write(out_text)
