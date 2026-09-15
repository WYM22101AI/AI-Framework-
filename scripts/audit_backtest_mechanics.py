"""
Audit Step 2: Backtest Mechanics, Look-Ahead Bias & Slippage Audit.

Verification items:
1. Signal Timing: Signal generated at Close(T).
2. Entry Price: Order executed at Open(T+1) -> next_open.
3. Return Measurement: Return earned is (Close(T+1) - Open(T+1)) / Open(T+1).
4. Look-Ahead Check: Is Close(T) return ever included in strategy return? (Must be NO).
5. Cost Deduction: Position change abs(diff) * cost_per_trade deducted from gross return.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import duckdb, config
import pandas as pd
import numpy as np
from scripts.backtester import compute_strategy_returns, get_prices

conn = duckdb.connect(config.DB_PATH, read_only=True)
prices = get_prices(conn, "AMZN")
conn.close()

report = ["=================================================================",
          "  AUDIT STEP 2: BACKTEST ENGINE LOOK-AHEAD & EXECUTION AUDIT     ",
          "=================================================================\n"]

# Create a deterministic mock signal: Long on exactly one day (day index 10)
mock_signal = pd.Series(0, index=prices["date"])
mock_signal.iloc[10] = 1 # Long signal emitted at Close of day 10

cost = 0.0005 # 5 bps
strat_df = compute_strategy_returns(mock_signal, prices, cost_per_trade=cost)

# Audit alignment
d10_date = prices["date"].iloc[10]
d11_date = prices["date"].iloc[11]

d10_row = strat_df.loc[d10_date]
d11_row = strat_df.loc[d11_date]

p_d10_close = prices.loc[prices["date"] == d10_date, "close"].values[0]
p_d11_open = prices.loc[prices["date"] == d11_date, "open"].values[0]
p_d11_close = prices.loc[prices["date"] == d11_date, "close"].values[0]

expected_d11_fwd_ret = (p_d11_close - p_d11_open) / p_d11_open
expected_d10_cost = 1 * cost # entered position on day 10 close -> executed day 11 open

report.append("1. EXECUTION ORDER AUDIT:")
report.append(f"   Signal Date (Close T): {d10_date} (Signal = {mock_signal.iloc[10]})")
report.append(f"   Execution Date (Open T+1): {d11_date}")
report.append(f"   Recorded Forward Return on Signal Date: {d10_row['forward_return']:.6f}")
report.append(f"   Actual (Open(T+1) to Close(T+1)) Return: {expected_d11_fwd_ret:.6f}")

if abs(d10_row['forward_return'] - expected_d11_fwd_ret) < 1e-9:
    report.append("   [PASS] Forward return perfectly matches (Close(T+1) - Open(T+1))/Open(T+1). Zero look-ahead leakage.")
else:
    report.append("   [FAIL] Return alignment mismatch!")

report.append("\n2. TRANSACTION COST DEDUCTION AUDIT:")
report.append(f"   Gross Strategy Return on Trade Day: {d10_row['forward_return']:.6f}")
report.append(f"   Cost Deducted: {d10_row['cost']:.6f} (Expected: {expected_d10_cost:.6f})")
report.append(f"   Net Strategy Return: {d10_row['strategy_return']:.6f}")

if abs(d10_row['strategy_return'] - (d10_row['forward_return'] - expected_d10_cost)) < 1e-9:
    report.append("   [PASS] 5 bps friction cost properly subtracted from net return.")
else:
    report.append("   [FAIL] Cost subtraction mismatch!")

# 3. Position Exit Friction Check
d11_cost = d11_row['cost'] # Position changed from 1 to 0
report.append(f"\n3. EXIT FRICTION CHECK:")
report.append(f"   Exit Day Cost on Position Close: {d11_cost:.6f}")
if d11_cost == cost:
    report.append("   [PASS] Round-trip friction correctly charges fee on both entry AND exit.")
else:
    report.append("   [FAIL] Exit fee not charged.")

out_text = "\n".join(report)
print(out_text)
with open("C:/Users/Yaming/family-quant-ai/data/audit_step2.txt", "w") as f:
    f.write(out_text)
