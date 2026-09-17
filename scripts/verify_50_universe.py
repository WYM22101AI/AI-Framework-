import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import duckdb, config
import pandas as pd

conn = duckdb.connect(config.DB_PATH, read_only=True)
out = ["=== 50-TICKER EXPANSION VERIFICATION REPORT ===\n"]

bars_count = conn.execute("SELECT COUNT(*) FROM daily_bars").fetchone()[0]
bars_syms = conn.execute("SELECT COUNT(DISTINCT symbol) FROM daily_bars").fetchone()[0]
feat_count = conn.execute("SELECT COUNT(*) FROM daily_features").fetchone()[0]
feat_syms = conn.execute("SELECT COUNT(DISTINCT symbol) FROM daily_features").fetchone()[0]

out.append(f"Price Bars:     {bars_count:,} bars across {bars_syms} tickers")
out.append(f"Daily Features: {feat_count:,} feature rows across {feat_syms} tickers")
out.append(f"Features / Bar: 24 quantitative metrics per row")

# Sector distribution check
sectors = {
    "Tech & Semis": ["TSLA", "AAPL", "NVDA", "MSFT", "META", "AMZN", "GOOG", "AMD", "AVGO", "QCOM", "INTC"],
    "Financials": ["JPM", "GS", "MS", "BAC", "V", "MA", "BLK"],
    "Healthcare": ["JNJ", "UNH", "LLY", "PFE", "ABBV", "MRK"],
    "Consumer": ["HD", "NKE", "MCD", "SBUX", "TGT", "WMT", "COST", "PG", "KO"],
    "Energy & Industrials": ["XOM", "CVX", "COP", "CAT", "GE", "BA", "UNP", "HON"],
    "Communication/Utils/RealEstate": ["DIS", "NFLX", "NEE", "PLD", "LIN"],
    "Index ETFs": ["SPY", "QQQ", "IWM", "DIA"]
}

out.append("\nSector Coverage Breakdown:")
for sec, syms in sectors.items():
    stored_syms = conn.execute(f"SELECT COUNT(DISTINCT symbol) FROM daily_bars WHERE symbol IN ({','.join([repr(s) for s in syms])})").fetchone()[0]
    out.append(f"  {sec:30s}: {stored_syms}/{len(syms)} tickers active")

conn.close()

out_text = "\n".join(out)
print(out_text)
with open("C:/Users/Yaming/family-quant-ai/data/50_universe_verification.txt", "w") as f:
    f.write(out_text)
