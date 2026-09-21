import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yfinance as yf
import pandas as pd
import numpy as np
import duckdb, config

# 1. Real Fed Funds from DuckDB
conn = duckdb.connect(config.DB_PATH, read_only=True)
fed_df = conn.execute("""
    SELECT release_date::DATE as date, value as rate_pct 
    FROM macro_releases 
    WHERE series_id = 'FEDFUNDS'
    ORDER BY release_date
""").fetchdf().set_index("date")
fed_df["daily_rf"] = (fed_df["rate_pct"] / 100.0) / 252.0

# 2. AMZN Data
amzn = yf.download("AMZN", start="2005-01-01", end="2026-03-01", auto_adjust=True)
if isinstance(amzn.columns, pd.MultiIndex):
    amzn.columns = amzn.columns.get_level_values(0)

ret5 = amzn["Close"].pct_change(5)
sma20 = amzn["Close"].rolling(20).mean()
dist_sma20 = (amzn["Close"] - sma20) / sma20
sig = ((ret5 < -0.04) & (dist_sma20 < -0.03)).astype(int).rolling(2).max().fillna(0)

fwd_ret = (amzn["Close"].shift(-1) - amzn["Open"].shift(-1)) / amzn["Open"].shift(-1)
trade_ret = (sig * fwd_ret) - (sig.diff().abs() * 0.0005)

# Map daily_rf to trading dates
rf_series = fed_df["daily_rf"].reindex(pd.to_datetime(amzn.index).date).bfill().ffill()
rf_series.index = amzn.index

# Strategy Total Return (Trading + Cash)
strat_total_daily = trade_ret + ((1.0 - sig) * rf_series)

p0 = amzn["Close"].iloc[0]
p1 = amzn["Close"].iloc[-1]

print("=== 21-YEAR (2005-2026) INDIVIDUAL & ASSET AUDIT ===")
print("AMZN Stock Buy & Hold (2005-2026):", f"{(p1 - p0) / p0:.2%}")
print("Pure Cash Yield Alone (Real Fed Funds):", f"{(1 + rf_series).prod() - 1:.2%}")
print("AMZN Tactical Alpha Trades Alone:", f"{(1 + trade_ret.dropna()).prod() - 1:.2%}")
print("AMZN Strategy Combined (Trades + Cash):", f"{(1 + strat_total_daily.dropna()).prod() - 1:.2%}")
