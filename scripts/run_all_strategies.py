"""
Run all strategies across all stocks and produce a summary report.
Usage: python scripts/run_all_strategies.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.signal_generator import STRATEGIES, run_strategy_test
from scripts.backtester import print_backtest_report

STOCKS = ["TSLA", "AAPL", "NVDA"]

results = []

for strategy_name in STRATEGIES:
    for symbol in STOCKS:
        print(f"\n{'='*60}")
        print(f"Testing: {strategy_name} on {symbol}")
        print(f"{'='*60}")

        result = run_strategy_test(strategy_name, symbol)
        if result:
            results.append(result)
            print_backtest_report(result)
        else:
            print(f"  No data / skipped")

# Summary table
print(f"\n\n{'='*80}")
print("STRATEGY SUMMARY — ALL TESTS")
print(f"{'='*80}")
print(f"{'Strategy':<25} {'OOS Return':>12} {'OOS Sharpe':>12} {'Skeptic':>10} {'Beats SPY':>10}")
print(f"{'-'*25} {'-'*12} {'-'*12} {'-'*10} {'-'*10}")

for r in results:
    oos = r["out_of_sample"]
    sr = r["skeptic_report"]
    print(f"{r['strategy']:<25} {oos['annualized_return']*100:>+11.1f}% {oos['sharpe_ratio']:>11.2f} {sr['verdict']:>10} {'YES' if r['beats_benchmark'] else 'NO':>10}")

# Count survivors
survivors = [r for r in results if r["skeptic_report"]["verdict"] in ("PASS", "WEAK")]
print(f"\n{len(survivors)} out of {len(results)} strategy-stock combinations survived the Skeptic.")

if survivors:
    print("\nSurvivors:")
    for s in survivors:
        print(f"  {s['strategy']}: OOS Sharpe {s['out_of_sample']['sharpe_ratio']:.2f}, verdict {s['skeptic_report']['verdict']}")
else:
    print("No strategies survived. This is normal — finding a real edge is hard.")
