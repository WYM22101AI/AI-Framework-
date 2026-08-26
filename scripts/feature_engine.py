"""
Feature Engine: compute daily features from raw data.
Transforms raw prices, macro, and earnings into ML-ready features.

Usage:
    python scripts/feature_engine.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import duckdb
import pandas as pd
import numpy as np
import config


def compute_technical_features(conn, symbol: str) -> pd.DataFrame:
    """Compute technical features for a single stock."""
    df = conn.execute(f"""
        SELECT timestamp::DATE as date, open, high, low, close, volume
        FROM daily_bars
        WHERE symbol = '{symbol}'
        ORDER BY timestamp
    """).fetchdf()

    if df.empty:
        return pd.DataFrame()

    # Returns
    df["return_1d"] = df["close"].pct_change(1)
    df["return_5d"] = df["close"].pct_change(5)
    df["return_20d"] = df["close"].pct_change(20)
    df["return_60d"] = df["close"].pct_change(60)

    # Volatility
    df["volatility_20d"] = df["return_1d"].rolling(20).std() * np.sqrt(252)

    # Moving averages
    df["ma_10"] = df["close"].rolling(10).mean()
    df["ma_20"] = df["close"].rolling(20).mean()
    df["ma_50"] = df["close"].rolling(50).mean()
    df["ma_200"] = df["close"].rolling(200).mean()

    # Distance from MAs
    df["distance_from_ma50"] = (df["close"] - df["ma_50"]) / df["ma_50"]
    df["distance_from_ma200"] = (df["close"] - df["ma_200"]) / df["ma_200"]

    # RSI (14-day)
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["rsi_14"] = 100 - (100 / (1 + rs))

    # Relative volume
    df["relative_volume"] = df["volume"] / df["volume"].rolling(20).mean()

    # Bollinger Bands
    bb_mid = df["close"].rolling(20).mean()
    bb_std = df["close"].rolling(20).std()
    df["bollinger_position"] = (df["close"] - bb_mid) / (2 * bb_std)  # -1 to +1

    df["symbol"] = symbol

    # Select final columns
    feature_cols = [
        "symbol", "date",
        "return_1d", "return_5d", "return_20d", "return_60d",
        "volatility_20d",
        "distance_from_ma50", "distance_from_ma200",
        "rsi_14", "relative_volume", "bollinger_position",
    ]
    return df[feature_cols].dropna()


def compute_relative_strength(conn, symbol: str, benchmark: str = "SPY") -> pd.Series:
    """Compute relative strength vs benchmark (20-day)."""
    stock = conn.execute(f"""
        SELECT timestamp::DATE as date, close FROM daily_bars
        WHERE symbol = '{symbol}' ORDER BY timestamp
    """).fetchdf().set_index("date")

    bench = conn.execute(f"""
        SELECT timestamp::DATE as date, close FROM daily_bars
        WHERE symbol = '{benchmark}' ORDER BY timestamp
    """).fetchdf().set_index("date")

    # Align dates
    aligned = stock.join(bench, lsuffix="_stock", rsuffix="_bench", how="inner")
    stock_ret = aligned["close_stock"].pct_change(20)
    bench_ret = aligned["close_bench"].pct_change(20)

    return stock_ret - bench_ret


def build_all_features(db_path: str = None) -> pd.DataFrame:
    """Build feature table for all tickers."""
    if db_path is None:
        db_path = config.DB_PATH

    conn = duckdb.connect(db_path, read_only=True)
    all_features = []

    for symbol in config.TICKERS:
        if symbol == "SPY":
            continue  # SPY is the benchmark, not a trading target

        print(f"  Computing features for {symbol}...")
        df = compute_technical_features(conn, symbol)
        if not df.empty:
            # Add relative strength
            rs = compute_relative_strength(conn, symbol, "SPY")
            df = df.set_index("date")
            df["relative_strength_vs_spy"] = rs
            df = df.reset_index()
            all_features.append(df)

    conn.close()

    if not all_features:
        return pd.DataFrame()

    return pd.concat(all_features, ignore_index=True)


if __name__ == "__main__":
    print("Building daily features...")
    features = build_all_features()
    print(f"\nGenerated {len(features)} feature rows for {features['symbol'].nunique()} stocks.")
    print(f"Date range: {features['date'].min()} to {features['date'].max()}")
    print(f"\nSample (TSLA, latest):")
    print(features[features["symbol"] == "TSLA"].tail(3).to_string(index=False))
