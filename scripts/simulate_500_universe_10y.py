import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import duckdb
import pandas as pd
import numpy as np
import config

conn = duckdb.connect(config.DB_PATH, read_only=True)
symbols = [r[0] for r in conn.execute("SELECT DISTINCT symbol FROM daily_bars").fetchall()]

print(f"Running 500-Stock Universe Multi-Asset Simulation across {len(symbols)} stocks...")

df_all = conn.execute("""
    SELECT timestamp::DATE as date, symbol, open, close 
    FROM daily_bars 
    WHERE timestamp >= '2016-01-01'
    ORDER BY timestamp
""").fetchdf()

df_all["ret5"] = df_all.groupby("symbol")["close"].pct_change(5)
df_all["sma20"] = df_all.groupby("symbol")["close"].transform(lambda s: s.rolling(20).mean())
df_all["dist_sma20"] = (df_all["close"] - df_all["sma20"]) / df_all["sma20"]

# Signal trigger
df_all["sig"] = ((df_all["ret5"] < -0.04) & (df_all["dist_sma20"] < -0.03)).astype(int)
df_all["sig"] = df_all.groupby("symbol")["sig"].transform(lambda s: s.rolling(2).max().fillna(0))

# Next-day forward return
df_all["next_open"] = df_all.groupby("symbol")["open"].shift(-1)
df_all["next_close"] = df_all.groupby("symbol")["close"].shift(-1)
df_all["fwd_ret"] = (df_all["next_close"] - df_all["next_open"]) / df_all["next_open"]
df_all["trade_ret"] = (df_all["sig"] * df_all["fwd_ret"]) - (df_all["sig"].diff().abs() * 0.0005)

# Daily aggregate portfolio return across all active signals
active_df = df_all[df_all["sig"] == 1]
daily_trades = active_df.groupby("date")["trade_ret"].mean()
daily_count = active_df.groupby("date")["sig"].count()

# Portfolio: allocate 5% per stock, max 50% equity (10 positions max)
dates = pd.date_range(start="2016-01-01", end=df_all["date"].max(), freq="B").date
portfolio_daily = pd.DataFrame(index=dates)
portfolio_daily.index.name = "date"

positions_held = daily_count.reindex(portfolio_daily.index).fillna(0).clip(upper=10)
avg_trade_pnl = daily_trades.reindex(portfolio_daily.index).fillna(0)

portfolio_daily["stock_pnl"] = positions_held * 0.05 * avg_trade_pnl
portfolio_daily["exposure"] = positions_held * 0.05

# Real Fed Funds yield + Money Market spread (+0.25% premium on cash)
fed_df = conn.execute("""
    SELECT release_date::DATE as date, value as rate_pct 
    FROM macro_releases 
    WHERE series_id = 'FEDFUNDS'
    ORDER BY release_date
""").fetchdf().set_index("date")
fed_df["daily_rf"] = ((fed_df["rate_pct"] + 0.25) / 100.0) / 252.0
rf_series = fed_df["daily_rf"].reindex(portfolio_daily.index).bfill().ffill()

portfolio_daily["cash_yield"] = (1.0 - portfolio_daily["exposure"]) * rf_series
portfolio_daily["total_ret"] = portfolio_daily["stock_pnl"] + portfolio_daily["cash_yield"]

r_clean = portfolio_daily["total_ret"].dropna()
total_cum = (1 + r_clean).prod() - 1
cagr = (1 + total_cum) ** (1 / 10.0) - 1
sharpe = r_clean.mean() / r_clean.std() * np.sqrt(252)
cum_curve = (1 + r_clean).cumprod()
max_dd = (cum_curve / cum_curve.cummax() - 1).min()

print("\n================================================================================")
print("     10-YEAR (2016 - 2026) 500-STOCK UNIVERSE MULTI-ASSET PORTFOLIO RESULTS")
print("================================================================================")
print(f"10-Year Cumulative Strategy Return:  {total_cum:+9.2%}")
print(f"10-Year Annualized Return (CAGR):    {cagr:+9.2%} / year")
print(f"10-Year Portfolio Sharpe Ratio:      {sharpe:4.2f}")
print(f"10-Year Maximum Drawdown:            {max_dd:6.2%}")
print(f"Average Active Equity Exposure:      {portfolio_daily['exposure'].mean():.1%}")
print(f"Average Capital in Money Market:     {(1.0 - portfolio_daily['exposure']).mean():.1%}")
