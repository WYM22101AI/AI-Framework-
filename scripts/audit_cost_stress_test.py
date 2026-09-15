"""
Audit Step 4: Cost Sensitivity & Transaction Friction Stress-Test.

Evaluates our approved strategies (AMZN, NVDA on mr_vix_tuned) against increasing
levels of execution friction:
1. Baseline: 5 bps (0.05%)
2. 2x Cost: 10 bps (0.10%)
3. 3x Cost: 15 bps (0.15%)
4. 4x Cost: 20 bps (0.20%)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import duckdb, config
import pandas as pd
from scripts.backtester import get_prices, run_backtest
from scripts.signal_generator import strategy_mr_vix_tuned

conn = duckdb.connect(config.DB_PATH, read_only=True)

report = ["=================================================================",
          "  AUDIT STEP 4: TRANSACTION FRICTION STRESS-TEST (AMZN & NVDA)   ",
          "=================================================================\n"]

frictions = [
    ("1x Baseline (5 bps)", 0.0005),
    ("2x Stressed (10 bps)", 0.0010),
    ("3x Severe (15 bps)", 0.0015),
    ("4x Extreme (20 bps)", 0.0020),
]

for sym in ["AMZN", "NVDA"]:
    report.append(f"--- Asset: {sym} (mr_vix_tuned) ---")
    prices = get_prices(conn, sym)
    sig = strategy_mr_vix_tuned(conn, sym)
    
    table_rows = []
    for label, cost in frictions:
        bt = run_backtest(sig, prices, f"{sym}_{label}", cost_per_trade=cost)
        oos = bt["out_of_sample"]
        sk = bt["skeptic_report"]
        
        table_rows.append({
            "Cost Tier": label,
            "OOS Ann Return": f"{oos.get('annualized_return', 0)*100:+.2f}%",
            "OOS Sharpe": f"{oos.get('sharpe_ratio', 0):.2f}",
            "Max Drawdown": f"{oos.get('max_drawdown', 0)*100:.1f}%",
            "Skeptic Verdict": sk.get("verdict", "FAIL"),
            "Passed Tests": f"{sk.get('tests_passed', 0)}/5",
        })
    
    df_sym = pd.DataFrame(table_rows)
    report.append(df_sym.to_string(index=False))
    report.append("")

conn.close()

out_text = "\n".join(report)
print(out_text)
with open("C:/Users/Yaming/family-quant-ai/data/audit_step4.txt", "w") as f:
    f.write(out_text)
