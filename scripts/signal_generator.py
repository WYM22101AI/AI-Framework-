"""
Signal Generator: define trading strategies and compute daily scores.
Each strategy produces a score from -1 (bearish) to +1 (bullish).

Usage:
    python scripts/signal_generator.py
"""

# TODO: Phase 3 - Implement after feature_engine.py is tested
#
# Planned strategies:
#   A. Momentum: buy winners, sell losers (20d return + MA50 + relative strength)
#   B. Mean Reversion: buy oversold (RSI < 30), sell overbought (RSI > 70)
#   C. Earnings Drift: buy after positive surprise, sell after negative
#   D. Macro Regime: risk-on vs risk-off based on VIX + yields + SPY trend
#   E. Earnings Straddle: flag high-volatility events (needs options data)
#
# Output: signals table with (symbol, date, strategy, score, confidence)

print("Phase 3: Signal Generator - not yet implemented.")
print("Complete Phase 2 (feature_engine.py) first.")
