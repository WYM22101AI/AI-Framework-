"""
Stress test the VIX-conditional mean reversion strategy.
Tests robustness under adverse assumptions.
"""

import sys
sys.path.insert(0, "C:/Users/Yaming/family-quant-ai")

import duckdb
import pandas as pd
import numpy as np
import config
from scripts.signal_generator import strategy_mr_vix_tuned
from scripts.backtester import get_prices, compute_strategy_returns, compute_metrics

STOCKS = ["AMZN", "NVDA"]
SPLIT_DATE = "2023-01-01"


def run_stress_test(symbol, cost, label):
    conn = duckdb.connect(config.DB_PATH, read_only=True)
    signal = strategy_mr_vix_tuned(conn, symbol)
    prices = get_prices(conn, symbol)
    conn.close()

    result = compute_strategy_returns(signal, prices, cost_per_trade=cost)
    oos = result[result.index >= pd.Timestamp(SPLIT_DATE)]
    m = compute_metrics(oos["strategy_return"], label)
    return m, oos["strategy_return"]


print("=" * 70)
print("STRESS TEST: VIX-Conditional Mean Reversion")
print("=" * 70)

for symbol in STOCKS:
    print(f"\n{'='*50}")
    print(f"  {symbol}")
    print(f"{'='*50}")

    # Test 1: Base case (5 bps)
    m, rets = run_stress_test(symbol, 0.0005, "base (5 bps)")
    print(f"\n  Base case (5 bps cost):")
    print(f"    Sharpe: {m['sharpe_ratio']:.2f}, Return: {m['annualized_return']*100:+.1f}%/yr")

    # Test 2: Double costs (10 bps)
    m2, _ = run_stress_test(symbol, 0.001, "2x cost (10 bps)")
    print(f"\n  2x costs (10 bps):")
    print(f"    Sharpe: {m2['sharpe_ratio']:.2f}, Return: {m2['annualized_return']*100:+.1f}%/yr")
    print(f"    Still profitable: {'YES' if m2['annualized_return'] > 0 else 'NO'}")

    # Test 3: 3x costs (15 bps)
    m3, _ = run_stress_test(symbol, 0.0015, "3x cost (15 bps)")
    print(f"\n  3x costs (15 bps):")
    print(f"    Sharpe: {m3['sharpe_ratio']:.2f}, Return: {m3['annualized_return']*100:+.1f}%/yr")
    print(f"    Still profitable: {'YES' if m3['annualized_return'] > 0 else 'NO'}")

    # Test 4: Remove best 5 trades
    sorted_rets = rets.sort_values(ascending=False)
    without_best5 = sorted_rets.iloc[5:]  # Remove 5 best days
    m4 = compute_metrics(without_best5, "remove best 5")
    print(f"\n  Remove best 5 trades:")
    print(f"    Sharpe: {m4['sharpe_ratio']:.2f}, Return: {m4['annualized_return']*100:+.1f}%/yr")
    print(f"    Still profitable: {'YES' if m4['annualized_return'] > 0 else 'NO'}")

    # Test 5: Remove best 10 trades
    without_best10 = sorted_rets.iloc[10:]
    m5 = compute_metrics(without_best10, "remove best 10")
    print(f"\n  Remove best 10 trades:")
    print(f"    Sharpe: {m5['sharpe_ratio']:.2f}, Return: {m5['annualized_return']*100:+.1f}%/yr")
    print(f"    Still profitable: {'YES' if m5['annualized_return'] > 0 else 'NO'}")

    # Test 6: Split OOS into halves
    oos_mid = rets.index[len(rets)//2]
    first_half = rets[rets.index < oos_mid]
    second_half = rets[rets.index >= oos_mid]
    m_h1 = compute_metrics(first_half, "2023-mid2024")
    m_h2 = compute_metrics(second_half, "mid2024-2026")
    print(f"\n  First half OOS (2023-mid2024):")
    print(f"    Sharpe: {m_h1['sharpe_ratio']:.2f}, Return: {m_h1['annualized_return']*100:+.1f}%/yr")
    print(f"  Second half OOS (mid2024-2026):")
    print(f"    Sharpe: {m_h2['sharpe_ratio']:.2f}, Return: {m_h2['annualized_return']*100:+.1f}%/yr")
    consistent = m_h1['annualized_return'] > 0 and m_h2['annualized_return'] > 0
    print(f"    Consistent across periods: {'YES' if consistent else 'NO'}")

print(f"\n{'='*70}")
print("STRESS TEST COMPLETE")
print(f"{'='*70}")
