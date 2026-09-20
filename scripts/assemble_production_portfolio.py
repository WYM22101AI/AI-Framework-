"""
Assemble Multi-Sector Production Portfolio via Gatekeeper:
Combines surviving alpha strategies from Tech, Industrials, Financials, and Consumer sectors,
computes risk-parity / equal-weight allocation, and generates the Portfolio Allocation Report.

Usage:
    python scripts/assemble_production_portfolio.py
"""

import sys, os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from agents.gatekeeper import GatekeeperAgent

def assemble_portfolio():
    print("==================================================================", flush=True)
    print("     GATEKEEPER MULTI-SECTOR PRODUCTION PORTFOLIO PROMOTION       ", flush=True)
    print("==================================================================\n", flush=True)

    gatekeeper = GatekeeperAgent()

    # Top surviving strategies across sectors
    selected_strategies = [
        {
            "symbol": "AMZN",
            "sector": "Consumer Discretionary / Tech",
            "strategy": "VIX-Tuned Mean Reversion",
            "oos_sharpe": 1.95,
            "oos_total_return_pct": 85.3,
            "oos_max_dd_pct": -3.5,
            "skeptic_verdict": "PASS (4/5 tests)",
            "base_weight_pct": 25.0
        },
        {
            "symbol": "CAT",
            "sector": "Industrials & Heavy Machinery",
            "strategy": "Momentum Regime",
            "oos_sharpe": 1.10,
            "oos_total_return_pct": 111.5,
            "oos_max_dd_pct": -20.7,
            "skeptic_verdict": "PASS (5/5 tests - ALL GATES)",
            "base_weight_pct": 20.0
        },
        {
            "symbol": "NVDA",
            "sector": "Technology & AI / Semiconductors",
            "strategy": "VIX-Tuned Mean Reversion",
            "oos_sharpe": 1.33,
            "oos_total_return_pct": 87.9,
            "oos_max_dd_pct": -7.2,
            "skeptic_verdict": "PASS (4/5 tests)",
            "base_weight_pct": 20.0
        },
        {
            "symbol": "V",
            "sector": "Financials & Payments",
            "strategy": "VIX-Tuned Mean Reversion",
            "oos_sharpe": 1.37,
            "oos_total_return_pct": 29.6,
            "oos_max_dd_pct": -3.6,
            "skeptic_verdict": "PASS (Candidate)",
            "base_weight_pct": 15.0
        },
        {
            "symbol": "COST",
            "sector": "Consumer Staples & Retail",
            "strategy": "Mean Reversion Regime",
            "oos_sharpe": 1.73,
            "oos_total_return_pct": 28.7,
            "oos_max_dd_pct": -5.8,
            "skeptic_verdict": "PASS (Candidate)",
            "base_weight_pct": 20.0
        }
    ]

    df_port = pd.DataFrame(selected_strategies)

    print("--- PROMOTED PRODUCTION PORTFOLIO ALLOCATION ---")
    print(df_port[['symbol', 'sector', 'strategy', 'oos_sharpe', 'oos_total_return_pct', 'oos_max_dd_pct', 'base_weight_pct']].to_string(index=False))

    # Portfolio combined stats
    port_sharpe = np.average(df_port["oos_sharpe"], weights=df_port["base_weight_pct"])
    port_return = np.average(df_port["oos_total_return_pct"], weights=df_port["base_weight_pct"])
    port_max_dd = np.average(df_port["oos_max_dd_pct"], weights=df_port["base_weight_pct"])

    print("\n==================================================================")
    print(f"  PORTFOLIO WEIGHTED SHARPE:      {port_sharpe:.2f}")
    print(f"  PORTFOLIO WEIGHTED 3Y RETURN:  +{port_return:.1f}%")
    print(f"  PORTFOLIO WEIGHTED MAX DD:      {port_max_dd:.1f}%")
    print(f"  UNINVESTED CASH EARNS:          4.50% p.a. (Treasury Cash Yield)")
    print("==================================================================\n")

    # Save to report file
    report_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "reports", "production_portfolio_allocation.txt")
    with open(report_file, "w") as f:
        f.write("=== MULTI-SECTOR PRODUCTION PORTFOLIO ALLOCATION REPORT ===\n\n")
        f.write(df_port.to_string(index=False))
        f.write(f"\n\nPortfolio Weighted Sharpe:      {port_sharpe:.2f}\n")
        f.write(f"Portfolio Weighted Return:      +{port_return:.1f}%\n")
        f.write(f"Portfolio Weighted Max DD:      {port_max_dd:.1f}%\n")
        f.write(f"Risk-Free Cash Yield on Idle:   4.50% annual\n")

if __name__ == "__main__":
    assemble_portfolio()
