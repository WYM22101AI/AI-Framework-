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
from scripts.storage import init_db, upsert_generic


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
    df["bollinger_position"] = (df["close"] - bb_mid) / (2 * bb_std)

    df["symbol"] = symbol

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

    aligned = stock.join(bench, lsuffix="_stock", rsuffix="_bench", how="inner")
    stock_ret = aligned["close_stock"].pct_change(20)
    bench_ret = aligned["close_bench"].pct_change(20)

    return stock_ret - bench_ret


def get_regime_features(conn) -> pd.DataFrame:
    """Get daily macro regime features from FRED data."""
    # VIX (daily)
    vix = conn.execute("""
        SELECT observation_date as date, value as vix
        FROM macro_releases
        WHERE series_id = 'VIXCLS'
        ORDER BY observation_date
    """).fetchdf()

    if not vix.empty:
        vix["vix_change_5d"] = vix["vix"].pct_change(5)

    # Fed funds rate (monthly, forward-fill to daily)
    fed = conn.execute("""
        SELECT observation_date as date, value as fed_funds
        FROM macro_releases
        WHERE series_id = 'FEDFUNDS'
        ORDER BY observation_date
    """).fetchdf()

    # 10-year Treasury (daily)
    treasury = conn.execute("""
        SELECT observation_date as date, value as treasury_10y
        FROM macro_releases
        WHERE series_id = 'DGS10'
        ORDER BY observation_date
    """).fetchdf()

    # Build a date spine from VIX (most frequent daily series)
    if vix.empty:
        return pd.DataFrame(columns=["date", "vix", "vix_change_5d", "fed_funds", "treasury_10y"])

    regime = vix[["date", "vix", "vix_change_5d"]].copy()

    if not fed.empty:
        regime = pd.merge_asof(
            regime.sort_values("date"),
            fed[["date", "fed_funds"]].sort_values("date"),
            on="date", direction="backward"
        )

    if not treasury.empty:
        regime = pd.merge_asof(
            regime.sort_values("date"),
            treasury[["date", "treasury_10y"]].sort_values("date"),
            on="date", direction="backward"
        )

    return regime


def get_earnings_features(conn, symbol: str) -> pd.DataFrame:
    """Compute earnings-related features for a stock."""
    earnings = conn.execute(f"""
        SELECT reported_date, surprise_pct
        FROM earnings
        WHERE symbol = '{symbol}' AND reported_date IS NOT NULL
        ORDER BY reported_date
    """).fetchdf()

    if earnings.empty:
        return pd.DataFrame(columns=["date", "days_since_earnings", "last_eps_surprise", "earnings_within_7d"])

    # Get all trading dates for this stock
    dates = conn.execute(f"""
        SELECT DISTINCT timestamp::DATE as date
        FROM daily_bars
        WHERE symbol = '{symbol}'
        ORDER BY date
    """).fetchdf()

    if dates.empty:
        return pd.DataFrame(columns=["date", "days_since_earnings", "last_eps_surprise", "earnings_within_7d"])

    earnings_dates = pd.to_datetime(earnings["reported_date"])
    surprise_map = dict(zip(earnings["reported_date"], earnings["surprise_pct"]))

    results = []
    for _, row in dates.iterrows():
        d = pd.Timestamp(row["date"])

        # Days since last earnings
        past = earnings_dates[earnings_dates <= d]
        if len(past) > 0:
            last_earn = past.max()
            days_since = (d - last_earn).days
            last_surprise = surprise_map.get(last_earn.date(), None)
        else:
            days_since = None
            last_surprise = None

        # Earnings within next 7 days
        future = earnings_dates[(earnings_dates > d) & (earnings_dates <= d + pd.Timedelta(days=7))]
        within_7d = len(future) > 0

        results.append({
            "date": row["date"],
            "days_since_earnings": days_since,
            "last_eps_surprise": last_surprise,
            "earnings_within_7d": within_7d,
        })

    return pd.DataFrame(results)


def build_all_features(db_path: str = None) -> pd.DataFrame:
    """Build complete feature table for all tickers."""
    if db_path is None:
        db_path = config.DB_PATH

    conn = duckdb.connect(db_path, read_only=True)

    # Pre-compute shared data
    print("  Loading regime features...")
    regime = get_regime_features(conn)

    all_features = []

    for symbol in config.TICKERS:
        if symbol == "SPY":
            continue

        print(f"  Computing features for {symbol}...")

        # Technical features
        df = compute_technical_features(conn, symbol)
        if df.empty:
            continue

        # Relative strength
        rs = compute_relative_strength(conn, symbol, "SPY")
        df = df.set_index("date")
        df["relative_strength_vs_spy"] = rs
        df = df.reset_index()

        # Join regime features (by date)
        if not regime.empty:
            df = pd.merge_asof(
                df.sort_values("date"),
                regime.sort_values("date"),
                on="date", direction="backward"
            )
        else:
            df["vix"] = None
            df["vix_change_5d"] = None
            df["fed_funds"] = None
            df["treasury_10y"] = None

        # Earnings features
        earn_feat = get_earnings_features(conn, symbol)
        if not earn_feat.empty:
            df = df.merge(earn_feat, on="date", how="left")
        else:
            df["days_since_earnings"] = None
            df["last_eps_surprise"] = None
            df["earnings_within_7d"] = None

        all_features.append(df)

    conn.close()

    if not all_features:
        return pd.DataFrame()

    combined = pd.concat(all_features, ignore_index=True)

    # Ensure final column order matches DuckDB table schema
    final_cols = [
        "symbol", "date",
        "return_1d", "return_5d", "return_20d", "return_60d",
        "volatility_20d",
        "distance_from_ma50", "distance_from_ma200",
        "rsi_14", "relative_volume", "bollinger_position",
        "relative_strength_vs_spy",
        "vix", "vix_change_5d", "fed_funds", "treasury_10y",
        "days_since_earnings", "last_eps_surprise", "earnings_within_7d",
    ]
    for col in final_cols:
        if col not in combined.columns:
            combined[col] = None

    return combined[final_cols]


def store_features(db_path: str = None):
    """Build features and persist to DuckDB."""
    if db_path is None:
        db_path = config.DB_PATH

    print("Building daily features...")
    features = build_all_features(db_path)

    if features.empty:
        print("No features generated.")
        return

    print(f"Generated {len(features)} rows for {features['symbol'].nunique()} stocks.")

    # Persist to DuckDB
    conn = init_db(db_path)
    rows = upsert_generic(conn, "daily_features", features, ["symbol", "date"])
    conn.close()

    print(f"Stored {rows} rows in daily_features table.")
    return features


if __name__ == "__main__":
    features = store_features()
    if features is not None and not features.empty:
        print(f"\nDate range: {features['date'].min()} to {features['date'].max()}")
        print(f"\nSample (TSLA, latest 3 rows):")
        sample = features[features["symbol"] == "TSLA"].tail(3)
        print(sample.to_string(index=False))
