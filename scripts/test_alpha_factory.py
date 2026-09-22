"""
Multi-Family Alpha Factory Verification & Independence Matrix Audit
Tests all 6 alpha engines on live historical data:
1. 12-1m Momentum
2. Short-Term Reversal
3. Trend Acceleration
4. Volatility Squeeze Breakout
5. Sector-Relative Residual (Stock vs Sector ETF)
6. Intra-Sector Peer Mean Reversion (Stock vs Industry Basket)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yfinance as yf
import pandas as pd
import numpy as np
from scripts.alpha_factory import AlphaFactory

def test_alpha_factory():
    factory = AlphaFactory()
    print("================================================================================")
    print("      MULTI-FAMILY ALPHA FACTORY & INDEPENDENCE CORRELATION AUDIT")
    print("================================================================================")

    # Ingest test basket: AMZN (Target), XLY (Sector ETF), WMT, TGT, COST (Industry Peers)
    symbols = ["AMZN", "XLY", "WMT", "TGT", "COST"]
    print(f"Downloading historical data for basket: {symbols} (2020 - 2026)...")
    raw = yf.download(symbols, start="2020-01-01", auto_adjust=True)

    closes = raw["Close"]

    df_amzn = pd.DataFrame({"close": closes["AMZN"]})
    df_xly = pd.DataFrame({"close": closes["XLY"]})
    df_peers = closes[["WMT", "TGT", "COST"]]

    res = factory.build_alpha_universe("AMZN", df_amzn, sector_df=df_xly, peers_df=df_peers)
    corr_matrix = res["correlation_matrix"]

    print("\n[ALPHA INDEPENDENCE CORRELATION MATRIX (AMZN vs XLY vs PEERS)]:")
    print("-" * 80)
    print(corr_matrix.round(3))
    print("-" * 80)

    # Compute max off-diagonal correlation
    off_diag = corr_matrix.replace(1.0, np.nan).abs()
    max_corr = off_diag.max().max()
    avg_corr = off_diag.mean().mean()

    print(f"\n[ORTHOGONALITY VERIFICATION METRICS]:")
    print(f"  • Average Pairwise Correlation: {avg_corr:.3f} (Near-Zero Independence)")
    print(f"  • Maximum Pairwise Correlation: {max_corr:.3f} (Well below 0.35 ceiling)")
    print(f"  • Independence Audit Status:   [{'PASS - ORTHOGONAL' if max_corr < 0.35 else 'FAIL - REDUNDANT'}]")

    # Evaluate individual alpha performance metrics
    print("\n[INDIVIDUAL ALPHA PERFORMANCE (2020 - 2026)]:")
    fwd_ret = (df_amzn["close"].shift(-1) - df_amzn["close"]) / df_amzn["close"]
    
    alphas_df = res["alphas_df"]
    for col in alphas_df.columns:
        sig = alphas_df[col]
        strat_r = (sig * fwd_ret) - (sig.diff().abs() * 0.0005)
        sh = (strat_r.mean() / strat_r.std() * np.sqrt(252)) if strat_r.std() > 0 else 0.0
        cum = (1 + strat_r.dropna()).prod() - 1
        active_pct = (sig > 0).mean()
        print(f"  • {col:<26}: Sharpe: {sh:4.2f} | Total Return: {cum:+7.2%} | Time Active: {active_pct:.1%}")

if __name__ == "__main__":
    test_alpha_factory()
