"""DuckDB storage operations for market data."""

import duckdb
import pandas as pd

TABLE_NAME = "daily_bars"


def init_db(db_path: str) -> duckdb.DuckDBPyConnection:
    """Connect to DuckDB and create all tables if they don't exist."""
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

    # Agent memory tables
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_log (
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            agent_name TEXT,
            action TEXT,
            context TEXT,
            result TEXT,
            regime TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_hypotheses (
            id TEXT PRIMARY KEY,
            created_by TEXT,
            description TEXT,
            status TEXT DEFAULT 'proposed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tested_at TIMESTAMP,
            result TEXT
        )
    """)

    # Research memory tables
    conn.execute("""
        CREATE TABLE IF NOT EXISTS research_experiments (
            experiment_id TEXT PRIMARY KEY,
            strategy TEXT,
            symbol TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            split_date DATE,
            is_annualized_return DOUBLE,
            is_sharpe DOUBLE,
            oos_annualized_return DOUBLE,
            oos_sharpe DOUBLE,
            oos_max_drawdown DOUBLE,
            skeptic_verdict TEXT,
            skeptic_tests_passed INT,
            beats_benchmark BOOLEAN,
            overfit_warning BOOLEAN,
            notes TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_features (
            symbol TEXT,
            date DATE,
            return_1d DOUBLE,
            return_5d DOUBLE,
            return_20d DOUBLE,
            return_60d DOUBLE,
            volatility_20d DOUBLE,
            distance_from_ma50 DOUBLE,
            distance_from_ma200 DOUBLE,
            rsi_14 DOUBLE,
            relative_volume DOUBLE,
            bollinger_position DOUBLE,
            relative_strength_vs_spy DOUBLE,
            vix DOUBLE,
            vix_change_5d DOUBLE,
            fed_funds DOUBLE,
            treasury_10y DOUBLE,
            days_since_earnings INT,
            last_eps_surprise DOUBLE,
            earnings_within_7d BOOLEAN,
            PRIMARY KEY (symbol, date)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS macro_releases (
            series_id TEXT,
            observation_date DATE,
            release_date DATE,
            value DOUBLE,
            PRIMARY KEY (series_id, observation_date)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS earnings (
            symbol TEXT,
            fiscal_date_ending DATE,
            reported_date DATE,
            reported_eps DOUBLE,
            estimated_eps DOUBLE,
            surprise DOUBLE,
            surprise_pct DOUBLE,
            PRIMARY KEY (symbol, fiscal_date_ending)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS fundamentals (
            symbol TEXT,
            fiscal_date_ending DATE,
            filed_date DATE,
            revenue DOUBLE,
            net_income DOUBLE,
            total_assets DOUBLE,
            total_liabilities DOUBLE,
            operating_cash_flow DOUBLE,
            PRIMARY KEY (symbol, fiscal_date_ending)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS options_snapshot (
            symbol TEXT,
            snapshot_date DATE,
            atm_iv DOUBLE,
            put_call_volume_ratio DOUBLE,
            put_call_oi_ratio DOUBLE,
            total_call_volume BIGINT,
            total_put_volume BIGINT,
            PRIMARY KEY (symbol, snapshot_date)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id TEXT,
            symbol TEXT,
            headline TEXT,
            published_at TIMESTAMP WITH TIME ZONE,
            source TEXT,
            PRIMARY KEY (id, symbol)
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


def upsert_generic(conn: duckdb.DuckDBPyConnection, table: str, df: pd.DataFrame, key_cols: list[str]) -> int:
    """Generic upsert: delete matching keys then insert."""
    if df.empty:
        return 0

    conn.register("_new_data", df)

    key_condition = " AND ".join(
        f"{table}.{col} = _new_data.{col}" for col in key_cols
    )
    conn.execute(f"""
        DELETE FROM {table}
        WHERE EXISTS (
            SELECT 1 FROM _new_data WHERE {key_condition}
        )
    """)
    conn.execute(f"INSERT INTO {table} SELECT * FROM _new_data")
    conn.unregister("_new_data")

    return len(df)


def get_row_counts(conn: duckdb.DuckDBPyConnection) -> dict:
    """Return a dict of symbol -> row count."""
    rows = conn.execute(
        f"SELECT symbol, COUNT(*) as cnt FROM {TABLE_NAME} GROUP BY symbol ORDER BY symbol"
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def get_all_table_counts(conn: duckdb.DuckDBPyConnection) -> dict:
    """Return row counts for all tables."""
    tables = ["daily_bars", "macro_releases", "earnings", "fundamentals", "options_snapshot", "news"]
    counts = {}
    for t in tables:
        try:
            row = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()
            counts[t] = row[0]
        except Exception:
            counts[t] = 0
    return counts
