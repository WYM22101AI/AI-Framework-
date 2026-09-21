"""
Empirical Comparison:
1. 80% S&P 500 (SPY) + 20% Cash / SPAXX Benchmark
2. 100% S&P 500 (SPY) Benchmark
3. Our Quant Strategy at 1.0x (100% Cash / No Leverage)
4. Our Quant Strategy at 1.5x (150% Tactical Leverage on Active Trades with Real Margin Interest)

Across: 1Y, 3Y, 5Y, 10Y, 21.7Y (Data as of September 2026)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yfinance as yf
import pandas as pd
import numpy as np
import duckdb, config

def run_simulation():
    conn = duckdb.connect(config.DB_PATH, read_only=True)

    # 1. Historical Fed Funds + 25 bps money market spread
    fed_df = conn.execute("""
        SELECT release_date::DATE as date, value as rate_pct 
        FROM macro_releases 
        WHERE series_id = 'FEDFUNDS'
        ORDER BY release_date
    """).fetchdf().set_index("date")
    
    # Cash Yield = Fed Funds + 0.25%
    fed_df["daily_rf"] = ((fed_df["rate_pct"] + 0.25) / 100.0) / 252.0
    # Margin Borrow Rate (Interactive Brokers Pro / Prime Rate) = Fed Funds + 1.50%
    fed_df["daily_margin_cost"] = ((fed_df["rate_pct"] + 1.50) / 100.0) / 252.0

    # 2. Download Multi-Sector Asset Data (2005 - Sept 2026)
    symbols = ["SPY", "AMZN", "NVDA", "CAT", "COST", "FSLR", "MSFT", "GOOG", "JPM", "BRO", "UNH", "LLY"]
    raw = yf.download(symbols, start="2005-01-01", auto_adjust=True)
    closes = raw["Close"]
    opens = raw["Open"]

    # True SPY Close-to-Close
    spy_c2c = (closes["SPY"].shift(-1) - closes["SPY"]) / closes["SPY"]

    date_keys = pd.to_datetime(closes.index).tz_localize(None).normalize().date
    daily_rf = fed_df["daily_rf"].reindex(date_keys).bfill().ffill()
    daily_rf.index = closes.index

    daily_margin = fed_df["daily_margin_cost"].reindex(date_keys).bfill().ffill()
    daily_margin.index = closes.index

    # Benchmark 1: 80% SPY + 20% Cash / SPAXX
    blend_80_20 = (0.80 * spy_c2c) + (0.20 * daily_rf)

    # 3. Strategy Signals across assets
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

    # Raw combined strategy PnL per unit of capital
    raw_strat_pnl = (0.5 * df_mr.mean(axis=1)) + (0.5 * df_trend.mean(axis=1))

    # ------------------------------------------------------------------------------------
    # MODEL 1: Standard 1.0x (Unleveraged, ~70% Cash / 30% Active Equity)
    # ------------------------------------------------------------------------------------
    strat_1x = raw_strat_pnl + (0.70 * daily_rf)

    # ------------------------------------------------------------------------------------
    # MODEL 2: Tactical 1.5x (150% Exposure on Trades, Leveraged with Broker Margin Cost)
    # ------------------------------------------------------------------------------------
    # When active trades occur, scale exposure by 1.5x
    # Borrowed portion (0.5x leverage) pays daily_margin rate
    leveraged_pnl = (raw_strat_pnl * 1.50) - (0.50 * daily_margin)
    # When in cash, earn cash yield on base capital
    strat_1_5x = leveraged_pnl + (0.50 * daily_rf)

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

    print("\n==========================================================================================================================================")
    print(f"{'Horizon':<24} {'Metric':<10} {'Our Strategy (1.0x)':<22} {'Our Strategy (1.5x)':<22} {'80% SPY / 20% Cash':<22} {'100% SPY Benchmark':<20}")
    print("==========================================================================================================================================")

    for name, start_dt, end_dt, yrs in horizons:
        cum_1x, cagr_1x, vol_1x, sh_1x, dd_1x = get_stats(strat_1x.loc[start_dt:end_dt], yrs)
        cum_15x, cagr_15x, vol_15x, sh_15x, dd_15x = get_stats(strat_1_5x.loc[start_dt:end_dt], yrs)
        cum_80, cagr_80, vol_80, sh_80, dd_80 = get_stats(blend_80_20.loc[start_dt:end_dt], yrs)
        cum_spy, cagr_spy, vol_spy, sh_spy, dd_spy = get_stats(spy_c2c.loc[start_dt:end_dt], yrs)

        print(f"{name:<24} {'CAGR':<10} {cagr_1x:+7.2%} / yr             {cagr_15x:+7.2%} / yr             {cagr_80:+7.2%} / yr             {cagr_spy:+7.2%} / yr")
        print(f"{'':<24} {'Sharpe':<10} {sh_1x:6.2f}                  {sh_15x:6.2f}                  {sh_80:6.2f}                  {sh_spy:6.2f}")
        print(f"{'':<24} {'Max DD':<10} {dd_1x:6.2%}                  {dd_15x:6.2%}                  {dd_80:6.2%}                  {dd_spy:6.2%}")
        print(f"{'':<24} {'Total':<10} {cum_1x:+7.2%}                 {cum_15x:+7.2%}                 {cum_80:+7.2%}                 {cum_spy:+7.2%}")
        print("-" * 138)

if __name__ == "__main__":
    run_simulation()
