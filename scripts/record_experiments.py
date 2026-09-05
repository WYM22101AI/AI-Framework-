"""Record all strategy experiment results into research memory."""
import sys, os, uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from scripts.storage import init_db, upsert_generic
import config

# All 9 results from our tests
experiments = [
    {"strategy": "momentum", "symbol": "TSLA", "is_ret": 11.7, "is_sharpe": 0.48, "oos_ret": -28.9, "oos_sharpe": -0.68, "oos_dd": -77.0, "verdict": "FAIL", "passed": 0, "beats": False, "overfit": True, "notes": "Strong IS, collapses OOS. Classic overfitting."},
    {"strategy": "momentum", "symbol": "AAPL", "is_ret": -2.3, "is_sharpe": -0.04, "oos_ret": -10.2, "oos_sharpe": -0.46, "oos_dd": -55.6, "verdict": "FAIL", "passed": 0, "beats": False, "overfit": True, "notes": "Negative both IS and OOS."},
    {"strategy": "momentum", "symbol": "NVDA", "is_ret": -5.7, "is_sharpe": 0.00, "oos_ret": -24.5, "oos_sharpe": -0.67, "oos_dd": -79.7, "verdict": "FAIL", "passed": 0, "beats": False, "overfit": True, "notes": "Negative both IS and OOS."},
    {"strategy": "mean_reversion", "symbol": "TSLA", "is_ret": -8.8, "is_sharpe": -0.90, "oos_ret": -10.0, "oos_sharpe": -0.65, "oos_dd": -41.6, "verdict": "FAIL", "passed": 0, "beats": False, "overfit": False, "notes": "RSI+Bollinger doesn't work on high-vol TSLA."},
    {"strategy": "mean_reversion", "symbol": "AAPL", "is_ret": None, "is_sharpe": None, "oos_ret": 0.5, "oos_sharpe": 0.10, "oos_dd": -15.0, "verdict": "FAIL", "passed": 1, "beats": False, "overfit": False, "notes": "Barely positive OOS. Low drawdown but insignificant."},
    {"strategy": "mean_reversion", "symbol": "NVDA", "is_ret": None, "is_sharpe": None, "oos_ret": 5.4, "oos_sharpe": 0.58, "oos_dd": -7.0, "verdict": "FAIL", "passed": 2, "beats": False, "overfit": False, "notes": "Best result so far. Sharpe 0.58, low drawdown. Passed 2/5 tests. Worth investigating further with parameter tuning."},
    {"strategy": "earnings_drift", "symbol": "TSLA", "is_ret": None, "is_sharpe": None, "oos_ret": 0.0, "oos_sharpe": 0.0, "oos_dd": 0.0, "verdict": "FAIL", "passed": 0, "beats": False, "overfit": False, "notes": "No signal generated. 5% surprise threshold too strict for TSLA."},
    {"strategy": "earnings_drift", "symbol": "AAPL", "is_ret": None, "is_sharpe": None, "oos_ret": 0.0, "oos_sharpe": 0.0, "oos_dd": 0.0, "verdict": "FAIL", "passed": 0, "beats": False, "overfit": False, "notes": "No signal generated. AAPL earnings data incomplete (rate limit)."},
    {"strategy": "earnings_drift", "symbol": "NVDA", "is_ret": None, "is_sharpe": None, "oos_ret": 0.0, "oos_sharpe": 0.0, "oos_dd": 0.0, "verdict": "FAIL", "passed": 0, "beats": False, "overfit": False, "notes": "No signal generated. Needs lower surprise threshold."},
]

records = []
for e in experiments:
    records.append({
        "experiment_id": str(uuid.uuid4())[:8],
        "strategy": e["strategy"],
        "symbol": e["symbol"],
        "created_at": pd.Timestamp.now(),
        "split_date": pd.Timestamp("2023-01-01").date(),
        "is_annualized_return": e["is_ret"] / 100 if e["is_ret"] else None,
        "is_sharpe": e["is_sharpe"],
        "oos_annualized_return": e["oos_ret"] / 100,
        "oos_sharpe": e["oos_sharpe"],
        "oos_max_drawdown": e["oos_dd"] / 100,
        "skeptic_verdict": e["verdict"],
        "skeptic_tests_passed": e["passed"],
        "beats_benchmark": e["beats"],
        "overfit_warning": e["overfit"],
        "notes": e["notes"],
    })

df = pd.DataFrame(records)
conn = init_db(config.DB_PATH)
rows = upsert_generic(conn, "research_experiments", df, ["experiment_id"])
print(f"Recorded {rows} experiment results to research_experiments table.")

# Show what we learned
print("\nLessons learned:")
print("1. Simple momentum (20d return + MA50 + RS) fails badly OOS on all stocks")
print("2. Mean reversion shows a glimmer on NVDA (Sharpe 0.58) but not statistically significant")
print("3. Earnings drift produces no signal — threshold too strict, need more earnings data")
print("4. All strategies tested so far: 0 survivors out of 9 combinations")
print("5. This is the system working correctly — finding a real edge IS hard")

conn.close()
