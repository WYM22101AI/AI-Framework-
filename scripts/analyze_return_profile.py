"""
Detailed Empirical Analysis:
1. Return Clustering Profile (Prolonged calm vs high-alpha bursts)
2. Opportunity Breadth Comparison: 50-Ticker Universe vs 500-Ticker Universe
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import duckdb
import pandas as pd
import numpy as np
import config

def analyze():
    conn = duckdb.connect(config.DB_PATH, read_only=True)
    symbols = [r[0] for r in conn.execute("SELECT DISTINCT symbol FROM daily_bars").fetchall()]
    
    top_50 = [
        "TSLA", "AAPL", "NVDA", "MSFT", "META", "AMZN", "GOOG", "AMD",
        "JPM", "GS", "MS", "BAC", "V", "MA", "BLK",
        "JNJ", "UNH", "LLY", "PFE", "ABBV", "MRK",
        "HD", "NKE", "MCD", "SBUX", "TGT", "WMT", "COST", "PG", "KO",
        "XOM", "CVX", "COP", "CAT", "GE", "BA", "UNP", "HON",
        "DIS", "NFLX", "NEE", "PLD", "LIN", "SPY", "QQQ", "IWM", "DIA"
    ]

    print("================================================================================")
    print("       OPPORTUNITY BREADTH AUDIT: 50-TICKER BENCHMARK VS 500 S&P UNIVERSE")
    print("================================================================================")
    print(f"Total Stock Universe Ingested in DuckDB: {len(symbols)} tickers")

    # Count opportunities across symbols from 2023 to 2026
    trade_counts = {}
    for sym in symbols:
        df = conn.execute(f"""
            SELECT timestamp::DATE as date, open, close 
            FROM daily_bars 
            WHERE symbol = '{sym}' AND timestamp >= '2023-01-01'
            ORDER BY timestamp
        """).fetchdf()
        if len(df) < 50:
            continue
        df = df.set_index("date")
        ret5 = df["close"].pct_change(5)
        sma20 = df["close"].rolling(20).mean()
        dist_sma20 = (df["close"] - sma20) / sma20
        
        # Trigger signal: 5-day drop < -4% and dist_sma20 < -3%
        sig = ((ret5 < -0.04) & (dist_sma20 < -0.03)).astype(int)
        sig_swings = (sig.diff() == 1).sum()
        if sig_swings > 0:
            trade_counts[sym] = sig_swings

    top50_triggers = {k: v for k, v in trade_counts.items() if k in top_50}
    
    print(f"\n1. 50-Ticker Universe:")
    print(f"   • Total distinct stocks with triggered opportunities: {len(top50_triggers)} stocks")
    print(f"   • Total trade events generated (2023-2026): {sum(top50_triggers.values())} trades")
    print(f"   • Top Active Stocks in 50-Universe: {list(top50_triggers.keys())[:8]}")

    print(f"\n2. Expanded S&P 500 Universe:")
    print(f"   • Total distinct stocks with triggered opportunities: {len(trade_counts)} stocks")
    print(f"   • Total trade events generated (2023-2026): {sum(trade_counts.values())} trades")
    print(f"   • Opportunity Expansion Multiplier: {len(trade_counts) / max(1, len(top50_triggers)):.1f}x More Diverse Opportunities")

    # Monthly return analysis
    print("\n================================================================================")
    print("           RETURN CLUSTERING PROFILE: MONTH-BY-MONTH BEHAVIOR")
    print("================================================================================")
    
    # Portfolio return with cash sweep
    df_amzn = conn.execute("""
        SELECT timestamp::DATE as date, open, close 
        FROM daily_bars 
        WHERE symbol = 'AMZN' AND timestamp >= '2023-01-01'
        ORDER BY timestamp
    """).fetchdf().set_index("date")
    df_amzn["ret5"] = df_amzn["close"].pct_change(5)
    df_amzn["sma20"] = df_amzn["close"].rolling(20).mean()
    df_amzn["dist_sma20"] = (df_amzn["close"] - df_amzn["sma20"]) / df_amzn["sma20"]
    sig_amzn = ((df_amzn["ret5"] < -0.04) & (df_amzn["dist_sma20"] < -0.03)).astype(int).rolling(2).max().fillna(0)

    fwd_ret = (df_amzn["close"].shift(-1) - df_amzn["open"].shift(-1)) / df_amzn["open"].shift(-1)
    daily_rf = 0.045 / 252.0
    daily_strat = (sig_amzn * fwd_ret) - (sig_amzn.diff().abs() * 0.0005) + ((1.0 - sig_amzn) * daily_rf)
    daily_strat = daily_strat.dropna()
    daily_strat.index = pd.to_datetime(daily_strat.index)

    monthly_ret = daily_strat.resample("ME").apply(lambda r: (1 + r).prod() - 1)
    
    print(f"{'MONTH':<10} {'STRATEGY RETURN':<18} {'ACTIVE TRADE DAYS':<20} {'REGIME TYPE':<25}")
    print("-" * 75)
    
    for m, r in monthly_ret.items():
        m_str = m.strftime('%Y-%m')
        days = sig_amzn.loc[sig_amzn.index.astype(str).str.startswith(m_str)].sum()
        if days == 0:
            regime = "Quiet Cash Vault (+0.37% Yield)"
        elif r > 0.02:
            regime = "High Alpha Harvest Burst"
        else:
            regime = "Active Opportunistic"
        print(f"{m_str:<10} {r:+8.2%}          {int(days):<20} {regime:<25}")

if __name__ == "__main__":
    analyze()
