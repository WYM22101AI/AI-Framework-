"""
Backtesting Engine: test trading signals against historical data.
Produces performance metrics for each strategy.

Usage:
    python scripts/backtester.py
"""

# TODO: Phase 4 - Implement after signal_generator.py is working
#
# Design:
#   - Input: signals table (symbol, date, strategy, score)
#   - Execution: buy at next day's open based on signal
#   - Costs: 0.05% spread per trade
#   - Periods: train 2016-2022, test 2023-2026
#
# Metrics:
#   - Annualized return (365 calendar days)
#   - Sharpe ratio
#   - Max drawdown
#   - Win rate
#   - p-value (is return != 0?)
#   - Comparison vs SPY buy-and-hold
#
# Output: backtest_results table

print("Phase 4: Backtester - not yet implemented.")
print("Complete Phase 3 (signal_generator.py) first.")
