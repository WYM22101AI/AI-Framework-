"""
Parameter sweep for VIX-conditional mean reversion.
Tests combinations of RSI threshold, Bollinger position, and VIX threshold
across top-performing stocks. Finds the most robust parameter set.
"""

import sys
sys.path.insert(0, "C:/Users/Yaming/family-quant-ai")

import duckdb
import pandas as pd
import numpy as np
import config
from scripts.backtester import get_prices, compute_strategy_returns, compute_metrics

# Parameters to sweep
RSI_THRESHOLDS = [30, 35, 40]
BOLLINGER_THRESHOLDS = [-0.6, -0.8, -1.0]
VIX_THRESHOLDS = [15, 20, 25]

# Test on stocks where the strategy showed promise
STOCKS = ["AMZN", "NVDA", "TSLA", "AMD", "MSFT"]

SPLIT_DATE = "2023-01-01"


def generate_signal(features, rsi_thresh, boll_thresh, vix_thresh):
    """Generate mean reversion signal with given parameters."""
    signal = pd.Series(0, index=features["date"])

    vix_ok = features["vix"].notna() & (features["vix"] > vix_thresh)
    long = vix_ok & (features["rsi_14"] < rsi_thresh) & (features["bollinger_position"] < boll_thresh)
    short = vix_ok & (features["rsi_14"] > (100 - rsi_thresh)) & (features["bollinger_position"] > -boll_thresh)

    signal[long.values] = 1
    signal[short.values] = -1
    return signal


conn = duckdb.connect(config.DB_PATH, read_only=True)

results = []

for rsi in RSI_THRESHOLDS:
    for boll in BOLLINGER_THRESHOLDS:
        for vix in VIX_THRESHOLDS:
            param_label = f"RSI<{rsi}_BB<{boll}_VIX>{vix}"

            oos_sharpes = []
            oos_returns = []
            oos_drawdowns = []
            n_trades_total = 0
            positive_stocks = 0

            for symbol in STOCKS:
                features = conn.execute(f"""
                    SELECT date, rsi_14, bollinger_position, vix
                    FROM daily_features WHERE symbol = '{symbol}' ORDER BY date
                """).fetchdf()

                prices = get_prices(conn, symbol)

                if features.empty or prices.empty:
                    continue

                signal = generate_signal(features, rsi, boll, vix)
                strat = compute_strategy_returns(signal, prices)

                split = pd.Timestamp(SPLIT_DATE)
                oos = strat[strat.index >= split]

                if len(oos) < 20:
                    continue

                m = compute_metrics(oos["strategy_return"], f"{param_label}_{symbol}")
                oos_sharpes.append(m["sharpe_ratio"])
                oos_returns.append(m["annualized_return"])
                oos_drawdowns.append(m["max_drawdown"])
                n_trades_total += m["n_trades"]
                if m["annualized_return"] > 0:
                    positive_stocks += 1

            if oos_sharpes:
                results.append({
                    "params": param_label,
                    "rsi": rsi,
                    "boll": boll,
                    "vix": vix,
                    "avg_sharpe": np.mean(oos_sharpes),
                    "avg_return": np.mean(oos_returns) * 100,
                    "worst_dd": min(oos_drawdowns) * 100,
                    "total_trades": n_trades_total,
                    "positive_stocks": positive_stocks,
                    "n_stocks": len(oos_sharpes),
                })

conn.close()

# Sort by average Sharpe
results.sort(key=lambda x: x["avg_sharpe"], reverse=True)

print(f"{'Parameters':<28} {'Avg Sharpe':>10} {'Avg Ret%':>9} {'Worst DD':>9} {'Trades':>7} {'Pos Stocks':>10}")
print("-" * 80)
for r in results:
    print(f"{r['params']:<28} {r['avg_sharpe']:>10.2f} {r['avg_return']:>+8.1f}% {r['worst_dd']:>8.0f}% {r['total_trades']:>7} {r['positive_stocks']}/{r['n_stocks']:>8}")

print(f"\nBest: {results[0]['params']} (avg Sharpe {results[0]['avg_sharpe']:.2f})")
print(f"Worst: {results[-1]['params']} (avg Sharpe {results[-1]['avg_sharpe']:.2f})")
