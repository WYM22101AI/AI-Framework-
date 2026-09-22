import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yfinance as yf
import pandas as pd
import numpy as np

symbols = ["CAT", "BRO", "GE", "NVDA", "AMZN", "COST", "JPM", "UNH", "FSLR"]
raw = yf.download(symbols + ["SPY", "^VIX"], start="2020-01-01", auto_adjust=True)

closes = raw["Close"]
opens = raw["Open"]
spy = closes["SPY"]
vix = closes["^VIX"]

print("========================================================================================================")
print("             HEAD-TO-HEAD: MOMENTUM REGIME VS MEAN REVERSION (2020 - SEPT 2026)")
print("========================================================================================================")
print(f"{'Symbol':<8} {'Momentum Return':<18} {'Momentum Sharpe':<18} {'Mean Rev Return':<18} {'Mean Rev Sharpe':<18}")
print("-" * 88)

for sym in symbols:
    c = closes[sym]
    o = opens[sym]
    
    # 1. Momentum: 20d return > 0, price > MA50, RS > 0, VIX < 25
    ret20 = c.pct_change(20)
    ma50 = c.rolling(50).mean()
    rs_spy = c.pct_change(20) - spy.pct_change(20)
    sig_mom = ((ret20 > 0) & (c > ma50) & (rs_spy > 0) & (vix < 25.0)).astype(int)
    
    # 2. Mean Reversion: 5d drop < -4%, dist to SMA20 < -3%, VIX < 40
    ret5 = c.pct_change(5)
    sma20 = c.rolling(20).mean()
    dist_sma20 = (c - sma20) / sma20
    sig_mr = ((ret5 < -0.04) & (dist_sma20 < -0.03) & (vix < 40.0)).astype(int).rolling(2).max().fillna(0)
    
    fwd_ret = (c.shift(-1) - o.shift(-1)) / o.shift(-1)
    daily_rf = 0.045 / 252.0
    
    r_mom = ((sig_mom * fwd_ret) - (sig_mom.diff().abs() * 0.0005) + ((1.0 - sig_mom) * daily_rf)).dropna()
    r_mr = ((sig_mr * fwd_ret) - (sig_mr.diff().abs() * 0.0005) + ((1.0 - sig_mr) * daily_rf)).dropna()
    
    cum_mom = (1 + r_mom).prod() - 1
    sh_mom = (r_mom.mean() / r_mom.std() * np.sqrt(252)) if r_mom.std() > 0 else 0.0
    
    cum_mr = (1 + r_mr).prod() - 1
    sh_mr = (r_mr.mean() / r_mr.std() * np.sqrt(252)) if r_mr.std() > 0 else 0.0
    
    print(f"{sym:<8} {cum_mom:+8.2%}            {sh_mom:6.2f}            {cum_mr:+8.2%}            {sh_mr:6.2f}")

print("=" * 88)
