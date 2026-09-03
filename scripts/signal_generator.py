"""
Signal Generator: define trading strategies and compute daily scores.
Each strategy produces a signal: 1 (long), -1 (short), 0 (no position).

Usage:
    python scripts/signal_generator.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import duckdb
import pandas as pd
import numpy as np
import config
from scripts.backtester import get_prices, run_backtest, print_backtest_report


def strategy_momentum(conn, symbol: str) -> pd.Series:
    """
    Strategy A: Momentum
    Long when: 20d return > 0 AND price > MA50 AND relative strength vs SPY > 0
    Short when: 20d return < 0 AND price < MA50 AND relative strength vs SPY < 0
    Otherwise: flat (0)
    """
    features = conn.execute(f"""
        SELECT date, return_20d, distance_from_ma50, relative_strength_vs_spy
        FROM daily_features
        WHERE symbol = '{symbol}'
        ORDER BY date
    """).fetchdf()

    if features.empty:
        return pd.Series(dtype=float)

    signal = pd.Series(0, index=features["date"])

    long_mask = (
        (features["return_20d"] > 0) &
        (features["distance_from_ma50"] > 0) &
        (features["relative_strength_vs_spy"] > 0)
    )

    short_mask = (
        (features["return_20d"] < 0) &
        (features["distance_from_ma50"] < 0) &
        (features["relative_strength_vs_spy"] < 0)
    )

    signal[long_mask.values] = 1
    signal[short_mask.values] = -1

    return signal


def strategy_mean_reversion(conn, symbol: str) -> pd.Series:
    """
    Strategy B: Mean Reversion
    Long when: RSI < 30 AND below lower Bollinger band (position < -1)
    Short when: RSI > 70 AND above upper Bollinger band (position > 1)
    Otherwise: flat
    """
    features = conn.execute(f"""
        SELECT date, rsi_14, bollinger_position
        FROM daily_features
        WHERE symbol = '{symbol}'
        ORDER BY date
    """).fetchdf()

    if features.empty:
        return pd.Series(dtype=float)

    signal = pd.Series(0, index=features["date"])

    long_mask = (features["rsi_14"] < 30) & (features["bollinger_position"] < -1)
    short_mask = (features["rsi_14"] > 70) & (features["bollinger_position"] > 1)

    signal[long_mask.values] = 1
    signal[short_mask.values] = -1

    return signal


def strategy_earnings_drift(conn, symbol: str) -> pd.Series:
    """
    Strategy C: Post-Earnings Drift
    Long when: last EPS surprise > 5% AND within 20 days of report
    Short when: last EPS surprise < -5% AND within 20 days of report
    """
    features = conn.execute(f"""
        SELECT date, days_since_earnings, last_eps_surprise
        FROM daily_features
        WHERE symbol = '{symbol}'
        ORDER BY date
    """).fetchdf()

    if features.empty:
        return pd.Series(dtype=float)

    signal = pd.Series(0, index=features["date"])

    within_window = features["days_since_earnings"].notna() & (features["days_since_earnings"] <= 20)
    positive_surprise = features["last_eps_surprise"].notna() & (features["last_eps_surprise"] > 5)
    negative_surprise = features["last_eps_surprise"].notna() & (features["last_eps_surprise"] < -5)

    signal[(within_window & positive_surprise).values] = 1
    signal[(within_window & negative_surprise).values] = -1

    return signal


STRATEGIES = {
    "momentum": strategy_momentum,
    "mean_reversion": strategy_mean_reversion,
    "earnings_drift": strategy_earnings_drift,
}


def run_strategy_test(strategy_name: str, symbol: str, split_date: str = "2023-01-01"):
    """Run a single strategy on a single stock through the full backtest + Skeptic pipeline."""
    conn = duckdb.connect(config.DB_PATH, read_only=True)

    strategy_fn = STRATEGIES[strategy_name]
    signal = strategy_fn(conn, symbol)
    prices = get_prices(conn, symbol)
    conn.close()

    if signal.empty or prices.empty:
        print(f"No data for {strategy_name} on {symbol}")
        return None

    result = run_backtest(signal, prices, f"{strategy_name}_{symbol}", split_date=split_date)
    return result


if __name__ == "__main__":
    print("=== Strategy Test: Momentum on TSLA ===")
    result = run_strategy_test("momentum", "TSLA")
    if result:
        print_backtest_report(result)
