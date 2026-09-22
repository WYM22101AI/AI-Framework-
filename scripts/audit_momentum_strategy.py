import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yfinance as yf
import pandas as pd
import numpy as np

symbols = ["CAT", "BRO", "GE", "NVDA", "AMZN", "COST", "JPM", "UNH"]
print(f"Downloading historical data for {symbols} (2020 - Sept 2026)...")
raw = yf.download(symbols + ["SPY", "^VIX"], start="2020-01-01", auto_adjust=True)

closes = raw["Close"]
opens = raw["Open"]
spy = closes["SPY"]
vix = closes["^VIX"]

print("\n========================================================================================")
print("       MOMENTUM REGIME STRATEGY: INDIVIDUAL ASSET EMPIRICAL PERFORMANCE (2020-2026)")
print("========================================================================================")
print(f"{'Symbol':<8} {'Total Return':<16} {'Annualized CAGR':<18} {'Sharpe Ratio':<15} {'Max Drawdown':<15} {'Win Rate':<10}")
print("-" * 88)

for sym in symbols:
    c = closes[sym]
    o = opens[sym]
    
    # Strategy Momentum Regime Logic:
    # Long when: 20d return > 0 AND price > MA50 AND relative strength vs SPY > 0 AND VIX < 25
    ret20 = c.pct_change(20)
    ma50 = c.rolling(50).mean()
    rs_spy = c.pct_change(20) - spy.pct_change(20)
    vix_ok = vix < 25.0
    
    sig = ((ret20 > 0) & (c > ma50) & (rs_spy > 0) & vix_ok).astype(int)
    
    # Next day open-to-close return
    fwd_ret = (c.shift(-1) - o.shift(-1)) / o.shift(-1)
    cost = sig.diff().abs() * 0.0005
    daily_rf = 0.045 / 252.0
    strat_r = (sig * fwd_ret) - cost + ((1.0 - sig) * daily_rf)
    
    r = strat_r.dropna()
    cum_ret = (1 + r).prod() - 1
    years = len(r) / 252.0
    cagr = (1 + cum_ret) ** (1.0 / years) - 1 if years > 0 and (1 + cum_ret) > 0 else 0.0
    sharpe = (r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0
    
    cum_curve = (1 + r).cumprod()
    max_dd = (cum_curve / cum_curve.cummax() - 1).min()
    
    active = sig.loc[r.index] > 0
    active_ret = fwd_ret.loc[r.index][active]
    wins = (active_ret > 0).sum()
    win_rate = (wins / len(active_ret)) if len(active_ret) > 0 else 0.0
    
    print(f"{sym:<8} {cum_ret:+8.2%}          {cagr:+7.2%} / yr        {sharpe:6.2f}          {max_dd:6.2%}          {win_rate:5.1%}")

print("=" * 88)
