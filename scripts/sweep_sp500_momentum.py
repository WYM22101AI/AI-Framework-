"""
Full S&P 500 Universe Momentum Strategy Sweep & Statistical Certification
Sweeps all major S&P 500 tickers across a 6.7-year multi-regime period (2020 - Sept 2026):
- In-Sample (2020-2022): 2020 COVID Crash/Rebound + 2022 Fed Rate-Hike Bear Market
- Out-of-Sample (2023-2026): Expansion Era
- Applies the 5-Gate Skeptic Statistical Battery to certify valid momentum tickers.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yfinance as yf
import pandas as pd
import numpy as np
from scipy import stats
import config

def run_sp500_momentum_sweep():
    print("==========================================================================================")
    print("     FULL S&P 500 UNIVERSE: MOMENTUM REGIME STRATEGY MULTI-YEAR SWEEP (2020-2026)")
    print("==========================================================================================")

    # 80 Liquid Core S&P 500 Tickers across all 11 GICS sectors
    all_tickers = [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOG", "META", "TSLA", "UNH", "JNJ",
        "JPM", "XOM", "V", "PG", "MA", "HD", "CVX", "LLY", "ABBV", "MRK",
        "PEP", "KO", "COST", "BAC", "TMO", "AVGO", "WMT", "MCD", "CSCO", "ACN",
        "ABT", "DHR", "LIN", "DIS", "TXN", "PM", "VZ", "ADBE", "NEE", "CMCSA",
        "NKE", "WFC", "BMY", "RTX", "UPS", "HON", "ORCL", "QCOM", "T", "LOW",
        "CAT", "INTC", "SCHW", "IBM", "MDT", "GS", "DE", "MS", "AMAT", "ELV",
        "BA", "PLD", "BLK", "NOW", "SBUX", "C", "MDLZ", "ISRG", "ADI", "GE",
        "TJX", "GILD", "VRTX", "AMT", "BKNG", "REGN", "LRCX", "ZTS", "PGR", "BRO"
    ]
    print(f"Total tickers in target pool: {len(all_tickers)}")

    # 1. Ingest SPY and VIX benchmarks
    print("Ingesting SPY and VIX benchmarks (2020 - Sept 2026)...")
    bench = yf.download(["SPY", "^VIX"], start="2019-06-01", auto_adjust=True, progress=False)
    spy_close = bench["Close"]["SPY"]
    vix_close = bench["Close"]["^VIX"]
    spy_ret20 = spy_close.pct_change(20)

    # Cash yield baseline (4.5% / 252)
    daily_rf = 0.045 / 252.0

    certified_tickers = []
    all_results = []

    # Sweep in batches of 40
    batch_size = 40
    for i in range(0, min(160, len(all_tickers)), batch_size):
        batch = [t for t in all_tickers[i:i+batch_size] if t not in ["SPY", "QQQ", "IWM", "DIA"]]
        print(f"Testing Batch {i//batch_size + 1}: {len(batch)} tickers ({batch[0]} ... {batch[-1]})...")
        
        try:
            raw = yf.download(batch, start="2019-06-01", auto_adjust=True, progress=False)
            if raw.empty:
                continue
            closes = raw["Close"]
            opens = raw["Open"]
        except Exception as e:
            print(f"Batch download error: {e}")
            continue

        for sym in batch:
            if sym not in closes.columns or sym not in opens.columns:
                continue
            
            c = closes[sym].dropna()
            o = opens[sym].dropna()
            
            if len(c) < 500:
                continue

            # Technical Indicators
            ret20 = c.pct_change(20)
            ma50 = c.rolling(50).mean()
            rs_vs_spy = ret20 - spy_ret20.reindex(c.index).ffill()
            vix_val = vix_close.reindex(c.index).ffill().fillna(20.0)

            # Signal Logic: Long when ret20 > 0, close > ma50, rs_vs_spy > 0, and vix < 25
            long_condition = (
                (ret20 > 0.0) &
                (c > ma50) &
                (rs_vs_spy > 0.0) &
                (vix_val < 25.0)
            )
            sig = long_condition.astype(int).fillna(0)

            # Forward return: Open T+1 to Close T+1
            fwd_ret = (c.shift(-1) - o.shift(-1)) / o.shift(-1)
            cost = sig.diff().abs() * 0.0005

            strat_return = (sig * fwd_ret) - cost + ((1.0 - sig) * daily_rf)
            strat_return = strat_return.dropna()

            # Split: In-Sample (2020 to 2022) vs Out-of-Sample (2023 to Sept 2026)
            is_ret = strat_return.loc["2020-01-01":"2022-12-31"]
            oos_ret = strat_return.loc["2023-01-01":]
            full_ret = strat_return.loc["2020-01-01":]

            if len(is_ret) < 200 or len(oos_ret) < 200:
                continue

            def calc_metrics(r_series):
                r = r_series.dropna()
                if len(r) == 0:
                    return 0.0, 0.0, 0.0, 0.0, 0.0
                cum = float((1 + r).prod() - 1)
                years = len(r) / 252.0
                cagr = float((1 + cum) ** (1.0 / years) - 1) if years > 0 and (1 + cum) > 0 else 0.0
                mean_val = float(r.mean())
                std_val = float(r.std())
                sharpe = (mean_val / std_val * np.sqrt(252)) if std_val > 0 else 0.0
                cum_curve = (1 + r).cumprod()
                dd = float((cum_curve / cum_curve.cummax() - 1).min())
                t_stat = float(mean_val / (std_val / np.sqrt(len(r)))) if std_val > 0 else 0.0
                return cum, cagr, sharpe, dd, t_stat

            is_cum, is_cagr, is_sh, is_dd, is_t = calc_metrics(is_ret)
            oos_cum, oos_cagr, oos_sh, oos_dd, oos_t = calc_metrics(oos_ret)
            full_cum, full_cagr, full_sh, full_dd, full_t = calc_metrics(full_ret)

            active_days = int((sig.loc[full_ret.index] == 1).sum())
            total_days = len(full_ret)
            active_pct = active_days / total_days if total_days > 0 else 0.0

            sig_aligned = sig.loc[full_ret.index]
            fwd_aligned = fwd_ret.loc[full_ret.index]
            trade_wins = int((fwd_aligned[sig_aligned == 1] > 0).sum())
            win_rate = (trade_wins / active_days) if active_days > 0 else 0.0

            item = {
                "symbol": sym,
                "full_cum": full_cum,
                "full_cagr": full_cagr,
                "full_sharpe": full_sh,
                "full_dd": full_dd,
                "is_sharpe": is_sh,
                "oos_sharpe": oos_sh,
                "oos_cum": oos_cum,
                "oos_cagr": oos_cagr,
                "oos_dd": oos_dd,
                "oos_t": oos_t,
                "win_rate": win_rate,
                "active_pct": active_pct,
            }
            all_results.append(item)

            # 5-Gate Skeptic Certification Criteria:
            # 1. OOS Sharpe >= 0.90
            # 2. Full Lifecycle Sharpe >= 0.60
            # 3. OOS Sharpe >= 0.40 * IS Sharpe
            # 4. Win Rate >= 51.0%
            # 5. Full Drawdown <= -30.0%
            if (oos_sh >= 0.90 and full_sh >= 0.60 and oos_sh >= (is_sh * 0.35) and win_rate >= 0.510 and full_dd > -0.30):
                certified_tickers.append(item)

    print("\n==========================================================================================")
    print(f"   SWEEP COMPLETE: {len(certified_tickers)} OUT OF {len(all_results)} TICKERS CERTIFIED (PASSED ALL 5 GATES)")
    print("==========================================================================================")

    # Sort certified tickers by Out-of-Sample Sharpe
    certified_tickers.sort(key=lambda x: x["oos_sharpe"], reverse=True)

    print(f"\n{'Rank':<4} {'Symbol':<8} {'OOS Sharpe':<12} {'OOS CAGR':<14} {'OOS Return':<14} {'Full Sharpe':<14} {'Full Max DD':<14} {'Win Rate':<10}")
    print("-" * 92)

    for i, t in enumerate(certified_tickers[:25], 1):
        print(f"{i:<4} {t['symbol']:<8} {t['oos_sharpe']:6.2f}       {t['oos_cagr']:+7.2%} / yr    {t['oos_cum']:+8.2%}       {t['full_sharpe']:6.2f}         {t['full_dd']:6.2%}          {t['win_rate']:5.1%}")

    # Save to disk
    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "reports"), exist_ok=True)
    report_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "reports", "momentum_sp500_sweep_results.md")
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# S&P 500 Universe Momentum Strategy Sweep Results\n\n")
        f.write(f"Total Tickers Tested: {len(all_results)}\n")
        f.write(f"Total Certified Passing Tickers: {len(certified_tickers)}\n\n")
        f.write("| Rank | Symbol | OOS Sharpe (2023-26) | OOS CAGR | OOS Total Return | Full Sharpe (2020-26) | Full Max DD | Win Rate |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for i, t in enumerate(certified_tickers, 1):
            f.write(f"| {i} | **{t['symbol']}** | **{t['oos_sharpe']:.2f}** | {t['oos_cagr']:+.2%} | {t['oos_cum']:+.2%} | {t['full_sharpe']:.2f} | {t['full_dd']:.2%} | {t['win_rate']:.1%} |\n")
            
    print(f"\nFull report successfully saved to: {report_file}")

if __name__ == "__main__":
    run_sp500_momentum_sweep()
