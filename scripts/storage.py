"""DuckDB storage operations for market data."""

import duckdb
import pandas as pd

TABLE_NAME = "daily_bars"


def init_db(db_path: str) -> duckdb.DuckDBPyConnection:
    """Connect to DuckDB and create the daily_bars table if it doesn't exist."""
    conn = duckdb.connect(db_path)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            symbol TEXT,
            timestamp TIMESTAMP WITH TIME ZONE,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume DOUBLE,
            trade_count DOUBLE,
            vwap DOUBLE,
            PRIMARY KEY (symbol, timestamp)
        )
    """)
    return conn


def get_last_date(conn: duckdb.DuckDBPyConnection, symbol: str):
    """Get the most recent timestamp stored for a given symbol. Returns None if no data."""
    result = conn.execute(
        f"SELECT MAX(timestamp) FROM {TABLE_NAME} WHERE symbol = ?", [symbol]
    ).fetchone()
    return result[0] if result and result[0] else None


def upsert_bars(conn: duckdb.DuckDBPyConnection, df: pd.DataFrame):
    """Insert bars, replacing any existing rows with the same (symbol, timestamp)."""
    if df.empty:
        return 0

    conn.register("_new_bars", df)

    # Delete overlapping rows first, then insert
    conn.execute(f"""
        DELETE FROM {TABLE_NAME}
        WHERE (symbol, timestamp) IN (
            SELECT symbol, timestamp FROM _new_bars
        )
    """)
    conn.execute(f"INSERT INTO {TABLE_NAME} SELECT * FROM _new_bars")
    conn.unregister("_new_bars")

    return len(df)


def get_row_counts(conn: duckdb.DuckDBPyConnection) -> dict:
    """Return a dict of symbol -> row count."""
    rows = conn.execute(
        f"SELECT symbol, COUNT(*) as cnt FROM {TABLE_NAME} GROUP BY symbol ORDER BY symbol"
    ).fetchall()
    return {row[0]: row[1] for row in rows}
