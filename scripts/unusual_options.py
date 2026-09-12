"""
Unusual Options Activity Strategy.

Detects when a stock's options volume is abnormally high relative to its
recent history, which often precedes large moves. Trades in the direction
implied by the put/call skew.

Requires data from Massive (Polygon) in the options_activity table.
If no options data is available, strategies return empty signals.

Usage:
    from scripts.unusual_options import strategy_unusual_options
    signal = strategy_unusual_options(conn, "TSLA")
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np


def get_options_features(conn, symbol: str) -> pd.DataFrame:
    """
    Compute unusual options activity features from options_activity table.

    Features computed:
    - volume_ratio: today's total options volume / 20-day average
    - pc_ratio_zscore: put/call ratio z-score vs 20-day rolling mean/std
    - call_dominance: (call_vol - put_vol) / total_vol (positive = bullish flow)
    - unusual_score: combined signal of volume spike + directional skew
    """
    try:
        df = conn.execute(f"""
            SELECT date, total_options_volume, call_volume, put_volume, put_call_ratio
            FROM options_activity
            WHERE symbol = '{symbol}'
            ORDER BY date
        """).fetchdf()
    except Exception:
        return pd.DataFrame()

    if df.empty or len(df) < 25:
        return pd.DataFrame()

    df = df.sort_values("date").reset_index(drop=True)

    # Volume ratio: today vs 20-day average
    df["avg_volume_20d"] = df["total_options_volume"].rolling(20).mean()
    df["volume_ratio"] = df["total_options_volume"] / df["avg_volume_20d"]

    # Put/call ratio z-score
    pc_mean = df["put_call_ratio"].rolling(20).mean()
    pc_std = df["put_call_ratio"].rolling(20).std()
    df["pc_ratio_zscore"] = (df["put_call_ratio"] - pc_mean) / pc_std

    # Call dominance: positive means more calls (bullish), negative means more puts (bearish)
    df["call_dominance"] = (df["call_volume"] - df["put_volume"]) / df["total_options_volume"]

    # Unusual score: high volume + directional skew
    vol_z = (df["volume_ratio"] - df["volume_ratio"].rolling(60).mean()) / df["volume_ratio"].rolling(60).std()
    df["unusual_score"] = vol_z.fillna(0).abs() + df["pc_ratio_zscore"].fillna(0).abs()

    # Replace inf/nan
    for col in ["volume_ratio", "pc_ratio_zscore", "call_dominance", "unusual_score"]:
        df[col] = df[col].replace([np.inf, -np.inf], np.nan)

    return df[["date", "volume_ratio", "pc_ratio_zscore", "call_dominance", "unusual_score"]].dropna()


def strategy_unusual_options(conn, symbol: str) -> pd.Series:
    """
    Strategy J: Unusual Options Activity.

    Signal logic:
    - Volume ratio > 2.0 (options volume 2x normal)
    - If put/call ratio is extremely high (z > 1.5): SHORT (heavy put buying = bearish)
    - If put/call ratio is extremely low (z < -1.5): LONG (heavy call buying = bullish)
    - Otherwise (high volume but no direction): FLAT

    This captures "smart money" positioning before major moves.
    """
    features = get_options_features(conn, symbol)

    if features.empty:
        return pd.Series(dtype=float)

    signal = pd.Series(0, index=features["date"])

    high_volume = features["volume_ratio"] > 2.0

    # Heavy call buying (bullish) = pc_ratio below normal
    bullish_flow = features["pc_ratio_zscore"] < -1.5
    # Heavy put buying (bearish) = pc_ratio above normal
    bearish_flow = features["pc_ratio_zscore"] > 1.5

    long_mask = high_volume & bullish_flow
    short_mask = high_volume & bearish_flow

    signal[long_mask.values] = 1
    signal[short_mask.values] = -1

    return signal


def strategy_options_volume_breakout(conn, symbol: str) -> pd.Series:
    """
    Strategy K: Options Volume Breakout.

    Simpler variant: just trade on extreme volume regardless of direction.
    When options volume is 3x+ normal, the stock is about to make a big move.
    Trade in the direction of the same-day stock price move (momentum following
    the smart money).

    Requires joining with daily_bars for same-day stock return.
    """
    features = get_options_features(conn, symbol)

    if features.empty:
        return pd.Series(dtype=float)

    # Get same-day stock returns
    try:
        stock = conn.execute(f"""
            SELECT timestamp::DATE as date, close
            FROM daily_bars
            WHERE symbol = '{symbol}'
            ORDER BY timestamp
        """).fetchdf()
    except Exception:
        return pd.Series(dtype=float)

    if stock.empty:
        return pd.Series(dtype=float)

    stock["return_1d"] = stock["close"].pct_change()
    merged = features.merge(stock[["date", "return_1d"]], on="date", how="inner")

    if merged.empty:
        return pd.Series(dtype=float)

    signal = pd.Series(0, index=merged["date"])

    extreme_volume = merged["volume_ratio"] > 3.0

    # Follow the direction of the stock move on the high-volume day
    long_mask = extreme_volume & (merged["return_1d"] > 0.01)
    short_mask = extreme_volume & (merged["return_1d"] < -0.01)

    signal[long_mask.values] = 1
    signal[short_mask.values] = -1

    return signal
