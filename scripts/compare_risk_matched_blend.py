import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yfinance as yf
import pandas as pd
import numpy as np
import duckdb, config

conn = duckdb.connect(config.DB_PATH, read_only=True)

# 1. Historical Fed Funds + 25 bps money market spread
fed_df = conn.execute("""
    SELECT release_date::DATE as date, value as rate_pct 
    FROM macro_releases 
    WHERE series_id = 'FEDFUNDS'
    ORDER BY release_date
""").fetchdf().set_index("date")
fed_df["daily_rf"] = ((fed_df["rate_pct"] + 0.25) / 100.0) / 252.0

# 2. Download SPY and Core Strategy Symbols (2005 - Sept 2026)
symbols = ["SPY", "AMZN", "NVDA", "CAT", "COST", "FSLR", "MSFT", "GOOG", "JPM", "BRO"]
raw = yf.download(symbols, start="2005-01-01", auto_adjust=True)
closes = raw["Close"]
opens = raw["Open"]

# Benchmark Close-to-Close
spy_c2c = (closes["SPY"].shift(-1) - closes["SPY"]) / closes["SPY"]

date_keys = pd.to_datetime(closes.index).tz_localize(None).normalize().date
daily_rf = fed_df["daily_rf"].reindex(date_keys).bfill().ffill()
daily_rf.index = closes.index

# Risk-Matched Blends:
# Blend A: 25% SPY + 75% Cash / SPAXX (Direct risk-equivalent benchmark)
blend_25_75 = (0.25 * spy_c2c) + (0.75 * daily_rf)

# Blend B: 30% SPY + 70% Cash / SPAXX
blend_30_70 = (0.30 * spy_c2c) + (0.70 * daily_rf)

# Our Pushed Production Strategy PnL
mr_trades = []
trend_trades = []
for sym in [s for s in symbols if s != "SPY"]:
    c = closes[sym]
    o = opens[sym]
    ret5 = c.pct_change(5)
    sma20 = c.rolling(20).mean()
    dist_sma20 = (c - sma20) / sma20
    sig_mr = ((ret5 < -0.04) & (dist_sma20 < -0.03)).astype(int).rolling(2).max().fillna(0)
    sma50 = c.rolling(50).mean()
    sig_trend = ((c > sma50) & (sma20 > sma50)).astype(int).fillna(0)
    
    fwd_day = (c.shift(-1) - o.shift(-1)) / o.shift(-1)
    fwd_c2c = (c.shift(-1) - c) / c
    
    mr_trades.append((sig_mr * fwd_day) - (sig_mr.diff().abs() * 0.0005))
    trend_trades.append((sig_trend * fwd_c2c) - (sig_trend.diff().abs() * 0.0005))

df_mr = pd.concat(mr_trades, axis=1).fillna(0)
df_trend = pd.concat(trend_trades, axis=1).fillna(0)

# Pushed strategy daily return (Combining Mean Reversion + Trend Momentum + Cash Yield)
strat_daily = (0.5 * df_mr.mean(axis=1)) + (0.5 * df_trend.mean(axis=1)) + (0.70 * daily_rf)

current_dt = closes.index[-1].strftime("%Y-%m-%d")
horizons = [
    ("1-Year Trailing (2025-26)", "2025-09-01", current_dt, 1.0),
    ("3-Year Trailing (2023-26)", "2023-09-01", current_dt, 3.0),
    ("5-Year Trailing (2021-26)", "2021-09-01", current_dt, 5.0),
    ("10-Year Trailing (2016-26)", "2016-09-01", current_dt, 10.0),
    ("21.7-Year (2005-2026)", "2005-01-03", current_dt, 21.7),
]

def get_stats(s, yrs):
    r = s.dropna()
    cum = (1 + r).prod() - 1
    cagr = (1 + cum)**(1.0/yrs) - 1 if yrs > 0 and (1+cum) > 0 else 0
    vol = r.std() * np.sqrt(252)
    sh = (r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0
    cum_curve = (1 + r).cumprod()
    dd = (cum_curve / cum_curve.cummax() - 1).min()
    return cum, cagr, vol, sh, dd

print("\n========================================================================================================================")
print(f"{'Horizon':<26} {'Metric':<10} {'Our Strategy':<22} {'25% SPY + 75% Cash':<24} {'100% SPY Benchmark':<20}")
print("========================================================================================================================")

for name, start_dt, end_dt, yrs in horizons:
    cum_s, cagr_s, vol_s, sh_s, dd_s = get_stats(strat_daily.loc[start_dt:end_dt], yrs)
    cum_b, cagr_b, vol_b, sh_b, dd_b = get_stats(blend_25_75.loc[start_dt:end_dt], yrs)
    cum_spy, cagr_spy, vol_spy, sh_spy, dd_spy = get_stats(spy_c2c.loc[start_dt:end_dt], yrs)

    print(f"{name:<26} {'CAGR':<10} {cagr_s:+7.2%} / yr             {cagr_b:+7.2%} / yr               {cagr_spy:+7.2%} / yr")
    print(f"{'':<26} {'Sharpe':<10} {sh_s:6.2f}                  {sh_b:6.2f}                    {sh_spy:6.2f}")
    print(f"{'':<26} {'Max DD':<10} {dd_s:6.2%}                  {dd_b:6.2%}                    {dd_spy:6.2%}")
    print(f"{'':<26} {'Total':<10} {cum_s:+7.2%}                 {cum_b:+7.2%}                   {cum_spy:+7.2%}")
    print("-" * 120)
