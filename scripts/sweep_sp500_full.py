"""
S&P 500 Full Universe Strategy Sweep:
Evaluates 9 strategy archetypes across all 318 S&P 500 stocks in family_quant.duckdb.
"""
import sys, os, time
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from scripts.storage import init_db
from scripts.backtester import run_backtest
import scripts.signal_generator as sg

def run_sp500_sweep():
    print(f"===========================================================", flush=True)
    print(f"  FULL S&P 500 UNIVERSE STRATEGY SWEEP (318 SYMBOLS)       ", flush=True)
    print(f"===========================================================", flush=True)
    
    import duckdb
    conn = duckdb.connect(config.DB_PATH, read_only=True)
    
    # Get distinct symbols from daily_features
    symbols = [r[0] for r in conn.execute("SELECT DISTINCT symbol FROM daily_features WHERE symbol != 'SPY' ORDER BY symbol").fetchall()]
    print(f"Evaluating {len(symbols)} S&P 500 symbols across 9 strategy families...\n", flush=True)
    
    strategy_funcs = {
        "VIX-Tuned Mean Reversion": sg.strategy_mr_vix_tuned,
        "Mean Reversion Regime": sg.strategy_mean_reversion_regime,
        "Mean Reversion (RSI<30)": sg.strategy_mean_reversion,
        "AI Cascade Overreaction": sg.strategy_cascade_overreaction,
        "AI Cascade Momentum": sg.strategy_cascade_momentum,
        "Momentum (Trend)": sg.strategy_momentum,
        "Momentum Regime": sg.strategy_momentum_regime,
        "Earnings Drift": sg.strategy_earnings_drift,
        "Earnings Drift Relaxed": sg.strategy_earnings_drift_relaxed
    }
    
    results = []
    skeptic_passes = []
    
    start_time = time.time()
    
    for idx, symbol in enumerate(symbols):
        # Load daily price bars for symbol
        df_bars = conn.execute(f"""
            SELECT timestamp::DATE as date, open, high, low, close, volume 
            FROM daily_bars 
            WHERE symbol = '{symbol}'
            ORDER BY timestamp ASC
        """).fetchdf()
        
        if df_bars.empty or len(df_bars) < 200:
            continue
            
        df_bars['date'] = pd.to_datetime(df_bars['date'])
        
        for strat_name, strat_fn in strategy_funcs.items():
            try:
                sig_series = strat_fn(conn, symbol)
            except Exception:
                continue
                
            if sig_series is None or sig_series.empty or sig_series.sum() < 5:
                continue
                
            # Run backtest with Dual-Benchmark & 5 bps friction (2023-01-01 OOS split)
            bt_dict = run_backtest(
                signal=sig_series,
                prices=df_bars,
                strategy_name=f"{symbol}_{strat_name}",
                cost_per_trade=0.0005,
                split_date="2023-01-01"
            )
            
            if not bt_dict:
                continue
                
            is_m = bt_dict.get("in_sample", {})
            oos_m = bt_dict.get("out_of_sample", {})
            sk = bt_dict.get("skeptic_report", {})
            
            oos_sharpe = oos_m.get("sharpe_ratio", 0.0)
            oos_dd = oos_m.get("max_drawdown", -1.0)
            oos_tot_ret = oos_m.get("total_return", 0.0)
            
            oos_split = pd.Timestamp("2023-01-01")
            active_oos_trades = int(sig_series[sig_series.index >= oos_split].sum())
            
            verdict = sk.get("verdict", "FAIL")
            passed_tests = sk.get("tests_passed", 0)
            
            is_candidate = (
                oos_sharpe >= 0.5 and 
                oos_dd >= -0.30 and 
                active_oos_trades >= 10
            )
            
            record = {
                "symbol": symbol,
                "strategy": strat_name,
                "is_sharpe": round(float(is_m.get("sharpe_ratio", 0.0)), 2),
                "oos_sharpe": round(float(oos_sharpe), 2),
                "active_oos_trades": active_oos_trades,
                "oos_max_dd_pct": round(float(oos_dd) * 100, 1),
                "oos_total_ret_pct": round(float(oos_tot_ret) * 100, 1),
                "candidate": is_candidate,
                "skeptic_verdict": verdict,
                "skeptic_tests_passed": passed_tests
            }
            results.append(record)
            
            if verdict == "PASS" and is_candidate:
                skeptic_passes.append(record)
                print(f"  >>> [SKEPTIC PASS] {symbol:5s} | {strat_name:25s} | OOS Sharpe: {oos_sharpe:5.2f} | Ret: +{oos_tot_ret*100:5.1f}% | DD: {oos_dd*100:4.1f}% | Trades: {active_oos_trades:3d}", flush=True)

        if (idx + 1) % 50 == 0:
            print(f"  ... Evaluated {idx + 1}/{len(symbols)} symbols ({len(results)} backtests so far)", flush=True)

    elapsed = time.time() - start_time
    conn.close()
    
    res_df = pd.DataFrame(results)
    
    print(f"\n===========================================================", flush=True)
    print(f"  S&P 500 SWEEP COMPLETED in {elapsed:.1f}s ({len(results)} backtests executed)", flush=True)
    print(f"===========================================================", flush=True)
    print(f"Total Candidates with OOS Sharpe >= 0.5: {len(res_df[res_df['candidate']])}")
    print(f"Total Strategies passing SKEPTIC 5-TEST BATTERY: {len(skeptic_passes)}\n")
    
    report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "reports", "sp500_full_sweep_report.txt")
    with open(report_path, "w") as f:
        f.write("=== FULL S&P 500 UNIVERSE STRATEGY SWEEP REPORT ===\n\n")
        f.write(f"Executed: {len(results)} experiments across {len(symbols)} symbols\n")
        f.write(f"Skeptic Passes: {len(skeptic_passes)}\n\n")
        if skeptic_passes:
            pass_df = pd.DataFrame(skeptic_passes)[['symbol', 'strategy', 'oos_sharpe', 'active_oos_trades', 'oos_total_ret_pct', 'oos_max_dd_pct', 'skeptic_tests_passed']]
            f.write(pass_df.sort_values(by="oos_sharpe", ascending=False).to_string(index=False))
        f.write("\n\n--- Top 40 Candidates by Out-of-Sample Sharpe ---\n")
        f.write(res_df.sort_values(by="oos_sharpe", ascending=False).head(40).to_string(index=False))

    if skeptic_passes:
        pass_df = pd.DataFrame(skeptic_passes)[['symbol', 'strategy', 'oos_sharpe', 'active_oos_trades', 'oos_total_ret_pct', 'oos_max_dd_pct', 'skeptic_tests_passed']]
        print("--- TOP SKEPTIC-CERTIFIED ALPHA STRATEGIES ---")
        print(pass_df.sort_values(by="oos_sharpe", ascending=False).head(15).to_string(index=False))

if __name__ == "__main__":
    run_sp500_sweep()
