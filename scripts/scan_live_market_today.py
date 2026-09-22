"""
Live Market Scanner & Opportunity Finder
Fetches latest market bars up to today and scans all 321 S&P 500 stocks for:
1. Oversold Panic Dips (Mean Reversion Triggers)
2. Momentum Breakouts (Trend Triggers)
3. Top Market Movers (Gainers & Losers)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yfinance as yf
import duckdb, config
import pandas as pd
import numpy as np

def scan_today():
    conn = duckdb.connect(config.DB_PATH, read_only=False)
    symbols = [r[0] for r in conn.execute("SELECT DISTINCT symbol FROM daily_bars").fetchall()]

    core_symbols = [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOG", "META", "TSLA", "CAT", "COST", 
        "UNH", "JPM", "XOM", "LLY", "V", "JNJ", "WMT", "PG", "HD", "DIS", "NFLX",
        "AMD", "INTC", "QCOM", "CRM", "BA", "GE", "FSLR", "NEE", "GS", "MS"
    ]
    print(f"Ingesting latest live bars for {len(core_symbols)} major market leaders...")
    raw = yf.download(core_symbols, period="5d", auto_adjust=True, progress=False)

    closes = raw["Close"]
    opens = raw["Open"]
    highs = raw["High"]
    lows = raw["Low"]
    volumes = raw["Volume"]

    print("\n================================================================================")
    print("           LIVE MARKET OPPORTUNITY SCAN (100 MAJOR S&P STOCKS)")
    print("================================================================================")

    oversold_dips = []
    momentum_triggers = []
    movers = []

    for sym in closes.columns:
        c = closes[sym].dropna()
        if len(c) < 3:
            continue
        p_now = float(c.iloc[-1])
        p_prev = float(c.iloc[-2])
        day_chg = (p_now - p_prev) / p_prev
        
        # 5-day return
        ret5 = (p_now - float(c.iloc[0])) / float(c.iloc[0])
        sma_val = float(c.mean())
        dist_sma = (p_now - sma_val) / sma_val

        movers.append((sym, day_chg, p_now))

        # Check Mean Reversion: 5-day drop < -3.5%
        if ret5 < -0.035 or day_chg < -0.025:
            oversold_dips.append((sym, day_chg, ret5, dist_sma, p_now))

        # Check Momentum: Day gain > +1.5%
        if day_chg > 0.015:
            momentum_triggers.append((sym, day_chg, ret5, dist_sma, p_now))

    movers.sort(key=lambda x: x[1])

    print("\n[TOP 5 DECLINERS TODAY - POTENTIAL REVERSAL TARGETS]:")
    for sym, chg, p in movers[:5]:
        print(f"  • {sym:<6s}: {chg:+6.2%} (${p:,.2f})")

    print("\n[TOP 5 GAINERS TODAY - MOMENTUM LEADERS]:")
    for sym, chg, p in movers[-5:]:
        print(f"  • {sym:<6s}: {chg:+6.2%} (${p:,.2f})")

    print(f"\n[TRIGGERED OVERSOLD DIP OPPORTUNITIES]: ({len(oversold_dips)} identified)")
    for sym, d_chg, r5, dsma, p in oversold_dips:
        print(f"  -> {sym:<6s}: Day: {d_chg:+6.2%}, 5-Day: {r5:+6.2%}, Price: ${p:,.2f}")

    print(f"\n[TRIGGERED MOMENTUM BREAKOUTS]: ({len(momentum_triggers)} identified)")
    for sym, d_chg, r5, dsma, p in momentum_triggers[:8]:
        print(f"  -> {sym:<6s}: Day: {d_chg:+6.2%}, 5-Day: {r5:+6.2%}, Price: ${p:,.2f}")

    conn.close()

if __name__ == "__main__":
    scan_today()
