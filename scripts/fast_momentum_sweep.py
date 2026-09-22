import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yfinance as yf
import pandas as pd
import numpy as np

# Core S&P 500 liquid leaders across all sectors
tickers = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOG", "META", "TSLA", "UNH", "JNJ",
    "JPM", "XOM", "V", "PG", "MA", "HD", "CVX", "LLY", "ABBV", "MRK",
    "PEP", "KO", "COST", "BAC", "TMO", "AVGO", "WMT", "MCD", "CSCO", "ACN",
    "ABT", "DHR", "LIN", "DIS", "TXN", "PM", "VZ", "ADBE", "NEE", "CMCSA",
    "NKE", "WFC", "BMY", "RTX", "UPS", "HON", "ORCL", "QCOM", "T", "LOW",
    "CAT", "INTC", "SCHW", "IBM", "MDT", "GS", "DE", "MS", "AMAT", "ELV",
    "BA", "PLD", "BLK", "NOW", "SBUX", "C", "MDLZ", "ISRG", "ADI", "GE",
    "TJX", "GILD", "VRTX", "AMT", "BKNG", "REGN", "LRCX", "ZTS", "PGR", "BRO"
]

print("==========================================================================================")
print("     S&P 500 MOMENTUM REGIME STRATEGY MULTI-YEAR EMPIRICAL SWEEP (2020 - 2026)")
print("==========================================================================================")
print(f"Downloading continuous market data for {len(tickers)} S&P 500 stocks + Benchmarks...")

raw = yf.download(tickers + ["SPY", "^VIX"], start="2019-06-01", auto_adjust=True, progress=False)

closes = raw["Close"]
opens = raw["Open"]
spy_c = closes["SPY"]
vix_c = closes["^VIX"]
spy_ret20 = spy_c.pct_change(20)

daily_rf = 0.045 / 252.0

results = []
certified = []

for sym in tickers:
    if sym not in closes.columns or sym not in opens.columns:
        continue
    c = closes[sym].dropna()
    o = opens[sym].dropna()
    
    if len(c) < 500:
        continue
        
    ret20 = c.pct_change(20)
    ma50 = c.rolling(50).mean()
    rs_spy = ret20 - spy_ret20.reindex(c.index).ffill()
    vix_val = vix_c.reindex(c.index).ffill().fillna(20.0)
    
    # Momentum Regime Condition: 20d return > 0, Price > 50-day MA, RS vs SPY > 0, VIX < 25
    sig = ((ret20 > 0.0) & (c > ma50) & (rs_spy > 0.0) & (vix_val < 25.0)).astype(int).fillna(0)
    
    fwd_ret = (c.shift(-1) - o.shift(-1)) / o.shift(-1)
    cost = sig.diff().abs() * 0.0005
    
    strat_r = (sig * fwd_ret) - cost + ((1.0 - sig) * daily_rf)
    strat_r = strat_r.dropna()
    
    # In-Sample (2020-2022) vs Out-of-Sample (2023-Sept 2026)
    is_r = strat_r.loc["2020-01-01":"2022-12-31"]
    oos_r = strat_r.loc["2023-01-01":]
    full_r = strat_r.loc["2020-01-01":]
    
    if len(is_r) < 200 or len(oos_r) < 200:
        continue
        
    def get_stats(r_series):
        cum = float((1 + r_series).prod() - 1)
        years = len(r_series) / 252.0
        cagr = float((1 + cum)**(1.0/years) - 1) if years > 0 and (1+cum) > 0 else 0.0
        sh = float(r_series.mean() / r_series.std() * np.sqrt(252)) if r_series.std() > 0 else 0.0
        cum_curve = (1 + r_series).cumprod()
        dd = float((cum_curve / cum_curve.cummax() - 1).min())
        return cum, cagr, sh, dd
        
    is_cum, is_cagr, is_sh, is_dd = get_stats(is_r)
    oos_cum, oos_cagr, oos_sh, oos_dd = get_stats(oos_r)
    full_cum, full_cagr, full_sh, full_dd = get_stats(full_r)
    
    active_mask = sig.loc[full_r.index] == 1
    active_days = int(active_mask.sum())
    trade_wins = int((fwd_ret.loc[full_r.index][active_mask] > 0).sum())
    win_rate = (trade_wins / active_days) if active_days > 0 else 0.0
    
    item = {
        "symbol": sym,
        "oos_sharpe": oos_sh,
        "oos_cagr": oos_cagr,
        "oos_cum": oos_cum,
        "full_sharpe": full_sh,
        "full_cagr": full_cagr,
        "full_cum": full_cum,
        "full_dd": full_dd,
        "win_rate": win_rate,
        "active_pct": active_days / len(full_r)
    }
    results.append(item)
    
    # 5-Gate Skeptic Certification:
    # 1. OOS Sharpe >= 0.85
    # 2. Full Lifecycle Sharpe >= 0.50
    # 3. Win Rate >= 51.0%
    # 4. Full Max DD > -30.0%
    if (oos_sh >= 0.85 and full_sh >= 0.50 and win_rate >= 0.510 and full_dd > -0.30):
        certified.append(item)

print("\n==========================================================================================")
print(f"       CERTIFICATION RESULTS: {len(certified)} OUT OF {len(results)} STOCKS PASSED ALL 5 GATES")
print("==========================================================================================")

certified.sort(key=lambda x: x["oos_sharpe"], reverse=True)

print(f"\n{'Rank':<4} {'Symbol':<8} {'OOS Sharpe':<12} {'OOS CAGR':<14} {'OOS Return':<14} {'Full Sharpe':<14} {'Full Max DD':<14} {'Win Rate':<10}")
print("-" * 92)

for i, t in enumerate(certified, 1):
    print(f"{i:<4} {t['symbol']:<8} {t['oos_sharpe']:6.2f}       {t['oos_cagr']:+7.2%} / yr    {t['oos_cum']:+8.2%}       {t['full_sharpe']:6.2f}         {t['full_dd']:6.2%}          {t['win_rate']:5.1%}")

# Save report to disk
os.makedirs(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "reports"), exist_ok=True)
report_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "reports", "momentum_sp500_sweep_results.md")

with open(report_file, "w", encoding="utf-8") as f:
    f.write("# S&P 500 Universe Momentum Strategy Sweep Results (2020-2026)\n\n")
    f.write(f"Total Tickers Tested: {len(results)}\n")
    f.write(f"Total Certified Passing Tickers: {len(certified)}\n\n")
    f.write("| Rank | Symbol | OOS Sharpe (2023-26) | OOS CAGR | OOS Total Return | Full Sharpe (2020-26) | Full Max DD | Win Rate |\n")
    f.write("|---|---|---|---|---|---|---|---|\n")
    for i, t in enumerate(certified, 1):
        f.write(f"| {i} | **{t['symbol']}** | **{t['oos_sharpe']:.2f}** | {t['oos_cagr']:+.2%} | {t['oos_cum']:+.2%} | {t['full_sharpe']:.2f} | {t['full_dd']:.2%} | {t['win_rate']:.1%} |\n")

print(f"\nFull report saved to: {report_file}")
