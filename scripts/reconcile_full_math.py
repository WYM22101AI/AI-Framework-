"""
Ground-Up Mathematical Audit & Performance Reconciliation
Up to Current Date: September 2026

Compares 3 Quantitative Approaches against True S&P 500 (SPY Close-to-Close):
1. Pure Short-Term Mean Reversion (1-3 Day Swings + Cash)
2. Hybrid Multi-Strategy (Tactical Mean Reversion + Multi-Week Trend Following + Cash)
3. Full S&P 500 Buy & Hold Benchmark (SPY)

Across Horizons:
- 2026 YTD (Jan 2026 -> Sept 2026)
- 1-Year (Sept 2025 -> Sept 2026)
- 3-Year (Sept 2023 -> Sept 2026)
- 5-Year (Sept 2021 -> Sept 2026)
- 10-Year (Sept 2016 -> Sept 2026)
- 21.7-Year (Jan 2005 -> Sept 2026)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yfinance as yf
import pandas as pd
import numpy as np
import duckdb, config

def run_reconciliation():
    print("==========================================================================================")
    print("      FAMILY QUANT AI: FULL MATHEMATICAL AUDIT & BENCHMARK RECONCILIATION")
    print("                        (DATA AS OF SEPTEMBER 2026)")
    print("==========================================================================================")

    conn = duckdb.connect(config.DB_PATH, read_only=True)

    # 1. Historical Fed Funds + 25 bps money market spread
    fed_df = conn.execute("""
        SELECT release_date::DATE as date, value as rate_pct 
        FROM macro_releases 
        WHERE series_id = 'FEDFUNDS'
        ORDER BY release_date
    """).fetchdf().set_index("date")
    fed_df["daily_rf"] = ((fed_df["rate_pct"] + 0.25) / 100.0) / 252.0

    # 2. Ingest 21.7 Years of Multi-Sector Asset Data (2005 - Sept 2026)
    symbols = ["SPY", "AMZN", "NVDA", "CAT", "COST", "FSLR", "MSFT", "GOOG", "JPM", "BRO", "UNH", "LLY", "XOM"]
    print(f"Downloading continuous market data for {len(symbols)} assets up to today...")
    raw = yf.download(symbols, start="2005-01-01", auto_adjust=True)

    closes = raw["Close"]
    opens = raw["Open"]

    # True Benchmark: Close-to-Close
    spy_c2c = (closes["SPY"].shift(-1) - closes["SPY"]) / closes["SPY"]

    # Clean date keys and map cash yield
    date_keys = pd.to_datetime(closes.index).tz_localize(None).normalize().date
    daily_rf = fed_df["daily_rf"].reindex(date_keys).bfill().ffill()
    daily_rf.index = closes.index

    # ------------------------------------------------------------------------------------
    # STRATEGY 1: Pure Short-Term Mean Reversion (1-3 Day Panic Dip Buying)
    # ------------------------------------------------------------------------------------
    mr_trades = []
    mr_sigs = []

    # STRATEGY 2: Multi-Week Trend / Momentum Following (Holding Strong Trends 10-40 Days)
    trend_trades = []
    trend_sigs = []

    traded_symbols = [s for s in symbols if s != "SPY"]

    for sym in traded_symbols:
        c = closes[sym]
        o = opens[sym]
        
        # Mean Reversion signals (2-day holding on oversold dips)
        ret5 = c.pct_change(5)
        sma20 = c.rolling(20).mean()
        dist_sma20 = (c - sma20) / sma20
        sig_mr = ((ret5 < -0.04) & (dist_sma20 < -0.03)).astype(int).rolling(2).max().fillna(0)

        # Trend Following signals (Long when price > 50 SMA and 20 SMA > 50 SMA)
        sma50 = c.rolling(50).mean()
        sig_trend = ((c > sma50) & (sma20 > sma50)).astype(int).fillna(0)

        # Forward returns
        fwd_ret_day = (c.shift(-1) - o.shift(-1)) / o.shift(-1)
        fwd_ret_c2c = (c.shift(-1) - c) / c

        cost_mr = sig_mr.diff().abs() * 0.0005
        cost_trend = sig_trend.diff().abs() * 0.0005

        mr_trades.append((sig_mr * fwd_ret_day) - cost_mr)
        mr_sigs.append(sig_mr)

        trend_trades.append((sig_trend * fwd_ret_c2c) - cost_trend)
        trend_sigs.append(sig_trend)

    df_mr_trades = pd.concat(mr_trades, axis=1).fillna(0.0)
    df_mr_sigs = pd.concat(mr_sigs, axis=1).fillna(0.0)

    df_trend_trades = pd.concat(trend_trades, axis=1).fillna(0.0)
    df_trend_sigs = pd.concat(trend_sigs, axis=1).fillna(0.0)

    # ------------------------------------------------------------------------------------
    # PORTFOLIO 1: Tactical Mean Reversion (Max 50% Equity, Remainder in Cash)
    # ------------------------------------------------------------------------------------
    mr_count = df_mr_sigs.sum(axis=1)
    mr_active_pnl = df_mr_trades.sum(axis=1) / len(traded_symbols)
    mr_exposure = (mr_count * 0.10).clip(upper=0.50)
    port_mr = mr_active_pnl + ((1.0 - mr_exposure) * daily_rf)

    # ------------------------------------------------------------------------------------
    # PORTFOLIO 2: Hybrid Tactical Alpha + Trend Capture (Max 75% Equity, Remainder in Cash)
    # ------------------------------------------------------------------------------------
    hybrid_stock_pnl = (0.5 * df_mr_trades.sum(axis=1) / len(traded_symbols)) + \
                       (0.5 * df_trend_trades.sum(axis=1) / len(traded_symbols))
    hybrid_exposure = ((mr_count * 0.05) + (df_trend_sigs.sum(axis=1) * 0.08)).clip(upper=0.75)
    port_hybrid = hybrid_stock_pnl + ((1.0 - hybrid_exposure) * daily_rf)

    # ------------------------------------------------------------------------------------
    # Horizon Evaluation Table
    # ------------------------------------------------------------------------------------
    current_dt = closes.index[-1].strftime("%Y-%m-%d")
    
    horizons = [
        ("YTD 2026 (Jan - Current)", "2026-01-01", current_dt, 0.72),
        ("1-Year (Trailing)", "2025-09-01", current_dt, 1.00),
        ("3-Year (Trailing)", "2023-09-01", current_dt, 3.00),
        ("5-Year (Trailing)", "2021-09-01", current_dt, 5.00),
        ("10-Year (Trailing)", "2016-09-01", current_dt, 10.00),
        ("21.7-Year (Full History)", "2005-01-03", current_dt, 21.70),
    ]

    def get_stats(r_series, yrs):
        r = r_series.dropna()
        cum = (1 + r).prod() - 1
        cagr = (1 + cum) ** (1.0 / yrs) - 1 if yrs > 0 and (1 + cum) > 0 else 0.0
        vol = r.std() * np.sqrt(252)
        sharpe = (r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0
        cum_curve = (1 + r).cumprod()
        dd = (cum_curve / cum_curve.cummax() - 1).min()
        return cum, cagr, vol, sharpe, dd

    print(f"\nCurrent Market Date: {current_dt}")
    print(f"Current SPY Price:   ${float(closes['SPY'].iloc[-1]):.2f} (S&P 500 Index Level: ~7,650)")
    print("\n" + "=" * 125)
    print(f"{'Horizon':<24} {'Metric':<10} {'1. Pure Mean Reversion':<24} {'2. Hybrid Alpha + Trend':<26} {'3. S&P 500 (SPY)':<20}")
    print("=" * 125)

    for name, start_dt, end_dt, yrs in horizons:
        s_mr = port_mr.loc[start_dt:end_dt]
        s_hyb = port_hybrid.loc[start_dt:end_dt]
        s_spy = spy_c2c.loc[start_dt:end_dt]

        cum_mr, cagr_mr, _, sh_mr, dd_mr = get_stats(s_mr, yrs)
        cum_hyb, cagr_hyb, _, sh_hyb, dd_hyb = get_stats(s_hyb, yrs)
        cum_spy, cagr_spy, _, sh_spy, dd_spy = get_stats(s_spy, yrs)

        print(f"{name:<24} {'CAGR':<10} {cagr_mr:+7.2%} / yr              {cagr_hyb:+7.2%} / yr              {cagr_spy:+7.2%} / yr")
        print(f"{'':<24} {'Sharpe':<10} {sh_mr:6.2f}                   {sh_hyb:6.2f}                   {sh_spy:6.2f}")
        print(f"{'':<24} {'Max DD':<10} {dd_mr:6.2%}                   {dd_hyb:6.2%}                   {dd_spy:6.2%}")
        print(f"{'':<24} {'Total':<10} {cum_mr:+7.2%}                  {cum_hyb:+7.2%}                  {cum_spy:+7.2%}")
        print("-" * 125)

if __name__ == "__main__":
    run_reconciliation()
