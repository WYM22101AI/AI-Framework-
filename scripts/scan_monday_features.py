import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import duckdb, config
import pandas as pd

conn = duckdb.connect(config.DB_PATH, read_only=True)
df_feat = conn.execute("""
    SELECT symbol, date, return_5d, distance_from_ma50, rsi_14, bollinger_position, vix 
    FROM daily_features 
    WHERE date = '2026-09-21'
""").fetchdf()

print(f"Total stocks with fresh Monday Sept 21 features: {len(df_feat)}")
print("\n[TOP 10 DECLINES ACROSS THE UNIVERSE (MONDAY SEPT 21)]:")
top_dec = df_feat.sort_values("return_5d").head(10)
for _, r in top_dec.iterrows():
    print(f"  • {r['symbol']:<6s}: 5-Day: {r['return_5d']:+6.2%}, Dist MA50: {r['distance_from_ma50']:+6.2%}, RSI: {r['rsi_14']:.1f}")

# Check which stocks triggered Mean Reversion: 5-day drop < -4% and RSI < 38
mr_triggers = df_feat[(df_feat["return_5d"] < -0.04) & (df_feat["rsi_14"] < 38)]
print(f"\n[TRIGGERED OVERSOLD DIP CANDIDATES FOR TOMORROW]: {len(mr_triggers)}")
for _, r in mr_triggers.iterrows():
    print(f"  -> {r['symbol']:<6s}: 5-Day Drop: {r['return_5d']:+6.2%}, RSI(14): {r['rsi_14']:.1f}")
