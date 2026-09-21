"""
Comprehensive Multi-Horizon Annualized Risk/Return Allocation Sweep
Compares:
1. Conservative Fortress (25% Max Active Equity / 75% Cash)
2. Dynamic Growth (70% Max Active Equity / 30% Cash)
3. S&P 500 Buy & Hold Benchmark (SPY Close-to-Close)

Across: 1-Year, 2-Year, 3-Year, 5-Year, 10-Year, 21-Year
With Real Historical Cash Yield = Fed Funds Rate + 0.25% (25 bps SPAXX/Repo Spread)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yfinance as yf
import pandas as pd
import numpy as np
import duckdb, config

def run_allocation_sweep():
    conn = duckdb.connect(config.DB_PATH, read_only=True)

    # 1. Real Fed Funds with +25 bps money-market spread
    fed_df = conn.execute("""
        SELECT release_date::DATE as date, value as rate_pct 
        FROM macro_releases 
        WHERE series_id = 'FEDFUNDS'
        ORDER BY release_date
    """).fetchdf().set_index("date")
    
    # Model Cash Yield = Fed Funds + 0.25% (25 bps spread)
    fed_df["daily_rf"] = ((fed_df["rate_pct"] + 0.25) / 100.0) / 252.0

    # 2. Download Multi-Sector Asset Data & SPY Benchmark (2005 - 2026)
    symbols = ["SPY", "AMZN", "NVDA", "CAT", "COST", "FSLR", "MSFT", "GOOG", "JPM", "BRO"]
    print(f"Downloading historical data for {symbols} (2005 - 2026)...")
    raw = yf.download(symbols, start="2005-01-01", end="2026-03-01", auto_adjust=True)

    closes = raw["Close"]
    opens = raw["Open"]

    # True Benchmark: Close-to-Close
    spy_c2c = (closes["SPY"].shift(-1) - closes["SPY"]) / closes["SPY"]

    # Map daily_rf with timezone safety
    date_keys = pd.to_datetime(closes.index).tz_localize(None).normalize().date
    daily_rf = fed_df["daily_rf"].reindex(date_keys).bfill().ffill()
    daily_rf.index = closes.index

    # 3. Strategy Signals across assets
    asset_trades = []
    asset_sigs = []

    for sym in [s for s in symbols if s != "SPY"]:
        c = closes[sym]
        o = opens[sym]
        ret5 = c.pct_change(5)
        sma20 = c.rolling(20).mean()
        dist_sma20 = (c - sma20) / sma20

        # Mean-reversion trigger
        sig = ((ret5 < -0.04) & (dist_sma20 < -0.03)).astype(int).rolling(2).max().fillna(0)
        
        # Next-day open-to-close return
        fwd_ret = (c.shift(-1) - o.shift(-1)) / o.shift(-1)
        cost = sig.diff().abs() * 0.0005
        trade_pnl = (sig * fwd_ret) - cost

        asset_trades.append(trade_pnl)
        asset_sigs.append(sig)

    df_trades = pd.concat(asset_trades, axis=1).fillna(0.0)
    df_sigs = pd.concat(asset_sigs, axis=1).fillna(0.0)

    # Number of active concurrent signals on each date
    active_count = df_sigs.sum(axis=1)
    mean_trade_ret = df_trades.sum(axis=1) / active_count.replace(0, np.nan)
    mean_trade_ret = mean_trade_ret.fillna(0.0)

    # -------------------------------------------------------------
    # MODEL A: Conservative (Max 25% Equity Allocation / 75% Cash)
    # -------------------------------------------------------------
    exp_a = (active_count * 0.10).clip(upper=0.25)
    pnl_a = (exp_a * mean_trade_ret) + ((1.0 - exp_a) * daily_rf)

    # -------------------------------------------------------------
    # MODEL B: Dynamic Growth (Max 70% Equity Allocation / 30% Cash)
    # -------------------------------------------------------------
    exp_b = (active_count * 0.15).clip(upper=0.70)
    pnl_b = (exp_b * mean_trade_ret) + ((1.0 - exp_b) * daily_rf)

    # -------------------------------------------------------------
    # Multi-Horizon Evaluation Table
    # -------------------------------------------------------------
    horizons = [
        ("1-Year (2025 - 2026)", "2025-01-01", "2026-03-01", 1.15),
        ("2-Year (2024 - 2026)", "2024-01-01", "2026-03-01", 2.15),
        ("3-Year (2023 - 2026)", "2023-01-01", "2026-03-01", 3.15),
        ("5-Year (2021 - 2026)", "2021-01-01", "2026-03-01", 5.15),
        ("10-Year (2016 - 2026)", "2016-01-01", "2026-03-01", 10.15),
        ("21-Year (2005 - 2026)", "2005-01-01", "2026-03-01", 21.15),
    ]

    def calc_stats(series, years):
        r = series.dropna()
        cum = (1 + r).prod() - 1
        cagr = (1 + cum) ** (1.0 / years) - 1 if years > 0 and (1 + cum) > 0 else 0.0
        vol = r.std() * np.sqrt(252)
        sharpe = (r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0
        cum_curve = (1 + r).cumprod()
        dd = (cum_curve / cum_curve.cummax() - 1).min()
        return cum, cagr, vol, sharpe, dd

    print("\n" + "=" * 115)
    print(f"{'Horizon':<22} {'Metric':<10} {'Model A (25% Cap)':<20} {'Model B (70% Cap)':<20} {'S&P 500 (SPY)':<20}")
    print("=" * 115)

    for name, start_dt, end_dt, yrs in horizons:
        s_a = pnl_a.loc[start_dt:end_dt]
        s_b = pnl_b.loc[start_dt:end_dt]
        s_spy = spy_c2c.loc[start_dt:end_dt]

        cum_a, cagr_a, vol_a, sh_a, dd_a = calc_stats(s_a, yrs)
        cum_b, cagr_b, vol_b, sh_b, dd_b = calc_stats(s_b, yrs)
        cum_spy, cagr_spy, vol_spy, sh_spy, dd_spy = calc_stats(s_spy, yrs)

        print(f"{name:<22} {'CAGR':<10} {cagr_a:+7.2%} / yr           {cagr_b:+7.2%} / yr           {cagr_spy:+7.2%} / yr")
        print(f"{'':<22} {'Sharpe':<10} {sh_a:6.2f}                {sh_b:6.2f}                {sh_spy:6.2f}")
        print(f"{'':<22} {'Max DD':<10} {dd_a:6.2%}                {dd_b:6.2%}                {dd_spy:6.2%}")
        print(f"{'':<22} {'Total':<10} {cum_a:+7.2%}               {cum_b:+7.2%}               {cum_spy:+7.2%}")
        print("-" * 115)

if __name__ == "__main__":
    run_allocation_sweep()
