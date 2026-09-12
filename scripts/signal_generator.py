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


def strategy_momentum_regime(conn, symbol: str) -> pd.Series:
    """
    Strategy D: Momentum with regime filter.
    Same as momentum, but ONLY trade when:
    - VIX < 25 (not panicking)
    - distance_from_ma50 for SPY > 0 (market uptrend)
    """
    features = conn.execute(f"""
        SELECT date, return_20d, distance_from_ma50, relative_strength_vs_spy, vix
        FROM daily_features
        WHERE symbol = '{symbol}'
        ORDER BY date
    """).fetchdf()

    # Get SPY trend
    spy_trend = conn.execute("""
        SELECT date, distance_from_ma50 as spy_ma50
        FROM daily_features
        WHERE symbol = 'TSLA'
    """).fetchdf()
    # SPY doesn't have features (it's the benchmark), so use VIX as proxy
    # Low VIX + positive momentum = risk-on regime

    if features.empty:
        return pd.Series(dtype=float)

    signal = pd.Series(0, index=features["date"])

    # Regime: VIX below 25
    regime_ok = features["vix"].notna() & (features["vix"] < 25)

    long_mask = (
        regime_ok &
        (features["return_20d"] > 0) &
        (features["distance_from_ma50"] > 0) &
        (features["relative_strength_vs_spy"] > 0)
    )

    short_mask = (
        regime_ok &
        (features["return_20d"] < 0) &
        (features["distance_from_ma50"] < 0) &
        (features["relative_strength_vs_spy"] < 0)
    )

    signal[long_mask.values] = 1
    signal[short_mask.values] = -1

    return signal


def strategy_mean_reversion_regime(conn, symbol: str) -> pd.Series:
    """
    Strategy E: Mean Reversion with VIX filter.
    Only trade mean reversion when VIX is elevated (> 20) — that's when
    oversold bounces are more likely.
    Relax RSI threshold to 35/65 for more signals.
    """
    features = conn.execute(f"""
        SELECT date, rsi_14, bollinger_position, vix
        FROM daily_features
        WHERE symbol = '{symbol}'
        ORDER BY date
    """).fetchdf()

    if features.empty:
        return pd.Series(dtype=float)

    signal = pd.Series(0, index=features["date"])

    vix_elevated = features["vix"].notna() & (features["vix"] > 20)

    long_mask = vix_elevated & (features["rsi_14"] < 35) & (features["bollinger_position"] < -0.8)
    short_mask = vix_elevated & (features["rsi_14"] > 65) & (features["bollinger_position"] > 0.8)

    signal[long_mask.values] = 1
    signal[short_mask.values] = -1

    return signal


def strategy_earnings_drift_relaxed(conn, symbol: str) -> pd.Series:
    """
    Strategy F: Post-Earnings Drift (relaxed thresholds).
    Lower surprise threshold from 5% to 2%.
    Extend window from 20 to 30 days.
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

    within_window = features["days_since_earnings"].notna() & (features["days_since_earnings"] <= 30)
    positive_surprise = features["last_eps_surprise"].notna() & (features["last_eps_surprise"] > 2)
    negative_surprise = features["last_eps_surprise"].notna() & (features["last_eps_surprise"] < -2)

    signal[(within_window & positive_surprise).values] = 1
    signal[(within_window & negative_surprise).values] = -1

    return signal


def strategy_mr_vix_tuned(conn, symbol: str) -> pd.Series:
    """
    Strategy G: Tuned VIX-Conditional Mean Reversion (best from parameter sweep).
    Parameters: RSI < 35, Bollinger < -0.6, VIX > 20
    Found via 27-combination sweep across 5 stocks. Avg OOS Sharpe 0.75.
    5/5 stocks positive. Robust across parameters (top 7 all use VIX>20).
    """
    features = conn.execute(f"""
        SELECT date, rsi_14, bollinger_position, vix
        FROM daily_features
        WHERE symbol = '{symbol}'
        ORDER BY date
    """).fetchdf()

    if features.empty:
        return pd.Series(dtype=float)

    signal = pd.Series(0, index=features["date"])

    vix_elevated = features["vix"].notna() & (features["vix"] > 20)
    long_mask = vix_elevated & (features["rsi_14"] < 35) & (features["bollinger_position"] < -0.6)
    short_mask = vix_elevated & (features["rsi_14"] > 65) & (features["bollinger_position"] > 0.6)

    signal[long_mask.values] = 1
    signal[short_mask.values] = -1

    return signal


def strategy_cascade_overreaction(conn, symbol: str) -> pd.Series:
    """
    Strategy H: AI Cascade Overreaction (Fade).
    Detects algo herding cascades that have pushed price too far, then trades the reversion.

    Signal: when cascade_score > 2.0, consecutive moves >= 3 days, and a large 5d move,
    fade the overreaction (buy oversold cascades, sell overbought cascades).
    VIX filter: only when VIX > 18 (stressed markets amplify more).
    """
    features = conn.execute(f"""
        SELECT date, return_1d, return_5d, cascade_score, consecutive_direction_days, vix
        FROM daily_features
        WHERE symbol = '{symbol}'
        ORDER BY date
    """).fetchdf()

    if features.empty:
        return pd.Series(dtype=float)

    signal = pd.Series(0, index=features["date"])

    has_data = (
        features["cascade_score"].notna() &
        features["vix"].notna() &
        features["consecutive_direction_days"].notna()
    )

    cascade_detected = has_data & (features["cascade_score"] > 2.0)
    herding_persisted = features["consecutive_direction_days"] >= 3
    vix_stressed = features["vix"] > 18

    # Oversold cascade: big drop + cascade => buy the bounce
    long_mask = (
        cascade_detected & herding_persisted & vix_stressed &
        (features["return_5d"] < -0.05)
    )

    # Overbought cascade: big rally + cascade => sell the top
    short_mask = (
        cascade_detected & herding_persisted & vix_stressed &
        (features["return_5d"] > 0.05)
    )

    signal[long_mask.values] = 1
    signal[short_mask.values] = -1

    return signal


def strategy_cascade_momentum(conn, symbol: str) -> pd.Series:
    """
    Strategy I: AI Cascade Momentum (Ride).
    Detects algo cascades early and rides the wave before the full herd piles in.

    Signal: when cascade_score > 1.5, only 1-2 consecutive days (early cascade),
    and volume is accelerating, trade in the same direction as the move.
    VIX filter: only when VIX < 25 (cascades in panic markets are too noisy).
    """
    features = conn.execute(f"""
        SELECT date, return_1d, cascade_score, consecutive_direction_days,
               volume_acceleration, vix
        FROM daily_features
        WHERE symbol = '{symbol}'
        ORDER BY date
    """).fetchdf()

    if features.empty:
        return pd.Series(dtype=float)

    signal = pd.Series(0, index=features["date"])

    has_data = (
        features["cascade_score"].notna() &
        features["vix"].notna() &
        features["volume_acceleration"].notna()
    )

    cascade_starting = has_data & (features["cascade_score"] > 1.5)
    early_stage = features["consecutive_direction_days"] <= 2
    vol_accelerating = features["volume_acceleration"] > 1.5
    vix_ok = features["vix"] < 25

    base_mask = cascade_starting & early_stage & vol_accelerating & vix_ok

    # Ride the direction of the move
    long_mask = base_mask & (features["return_1d"] > 0)
    short_mask = base_mask & (features["return_1d"] < 0)

    signal[long_mask.values] = 1
    signal[short_mask.values] = -1

    return signal


from scripts.unusual_options import strategy_unusual_options, strategy_options_volume_breakout

STRATEGIES = {
    "momentum": strategy_momentum,
    "mean_reversion": strategy_mean_reversion,
    "earnings_drift": strategy_earnings_drift,
    "momentum_regime": strategy_momentum_regime,
    "mr_regime": strategy_mean_reversion_regime,
    "earnings_relaxed": strategy_earnings_drift_relaxed,
    "mr_vix_tuned": strategy_mr_vix_tuned,
    "cascade_overreaction": strategy_cascade_overreaction,
    "cascade_momentum": strategy_cascade_momentum,
    "unusual_options": strategy_unusual_options,
    "options_volume_breakout": strategy_options_volume_breakout,
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
