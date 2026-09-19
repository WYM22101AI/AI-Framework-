"""
Benchmark: TypeSafe Jev vs. Snowflake Cortex AI
Head-to-head comparison on Speed, Efficiency, Capability, Veto Accuracy, and Cost.

Usage:
    python scripts/benchmark_jev_vs_cortex.py
"""

import sys, os, time, json
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from agents.meta_labeler import MetaLabelerAgent

def run_benchmark():
    print("==================================================================", flush=True)
    print("      HEAD-TO-HEAD BENCHMARK: TYPESAFE JEV vs. SNOWFLAKE CORTEX   ", flush=True)
    print("==================================================================\n", flush=True)

    jev_agent = MetaLabelerAgent(engine="typesafe_jev")
    cortex_agent = MetaLabelerAgent(engine="snowflake_cortex")

    scenarios = [
        {
            "name": "1. Oversold Bounce (AMZN)",
            "expected_verdict": "APPROVED",
            "state": {
                "as_of": "2026-09-18",
                "symbol": "AMZN",
                "strategy": "vix_regime_mean_reversion",
                "return_1d_pct": -4.8,
                "return_5d_pct": -7.2,
                "rsi_14": 24.5,
                "volatility_20d_annualized": 0.28,
                "relative_volume": 1.65,
                "bollinger_position": -0.85,
                "distance_from_ma50_pct": -6.5,
                "cascade_score": -2.4,
                "vix_level": 24.5,
                "vix_5d_change": 4.2,
                "days_since_earnings": 45,
                "earnings_within_7d": False,
                "recent_news": ["AMZN expands cloud AI infrastructure in Europe", "Tech sector pulls back on macro rate concerns"]
            }
        },
        {
            "name": "2. Falling Knife / Crisis (XYZ)",
            "expected_verdict": "VETOED",
            "state": {
                "as_of": "2026-09-18",
                "symbol": "XYZ",
                "strategy": "vix_regime_mean_reversion",
                "return_1d_pct": -14.2,
                "return_5d_pct": -22.0,
                "rsi_14": 18.0,
                "volatility_20d_annualized": 0.55,
                "relative_volume": 4.5,
                "bollinger_position": -1.2,
                "distance_from_ma50_pct": -25.0,
                "cascade_score": -4.2,
                "vix_level": 22.0,
                "vix_5d_change": 2.0,
                "days_since_earnings": 30,
                "earnings_within_7d": False,
                "recent_news": ["SEC launches formal fraud investigation into accounting practices", "CEO abruptly resigns amid audit findings"]
            }
        },
        {
            "name": "3. Data Glitch / Split Artifact (GLTCH)",
            "expected_verdict": "VETOED",
            "state": {
                "as_of": "2026-09-18",
                "symbol": "GLTCH",
                "strategy": "vix_regime_mean_reversion",
                "return_1d_pct": -49.5,
                "return_5d_pct": -49.2,
                "rsi_14": 5.0,
                "volatility_20d_annualized": 0.15,
                "relative_volume": 0.05,
                "bollinger_position": -3.5,
                "distance_from_ma50_pct": -50.0,
                "cascade_score": -5.0,
                "vix_level": 15.0,
                "vix_5d_change": 0.0,
                "days_since_earnings": 60,
                "earnings_within_7d": False,
                "recent_news": []
            }
        },
        {
            "name": "4. Earnings Event Risk (TSLA)",
            "expected_verdict": "VETOED",
            "state": {
                "as_of": "2026-09-18",
                "symbol": "TSLA",
                "strategy": "vix_regime_mean_reversion",
                "return_1d_pct": -3.5,
                "return_5d_pct": -5.0,
                "rsi_14": 32.0,
                "volatility_20d_annualized": 0.40,
                "relative_volume": 1.2,
                "bollinger_position": -0.6,
                "distance_from_ma50_pct": -4.0,
                "cascade_score": -1.8,
                "vix_level": 20.0,
                "vix_5d_change": 1.0,
                "days_since_earnings": 1,
                "earnings_within_7d": True,
                "recent_news": ["TSLA reports Q3 earnings tomorrow after market close"]
            }
        },
        {
            "name": "5. Sector-Wide Pullback (NVDA)",
            "expected_verdict": "APPROVED",
            "state": {
                "as_of": "2026-09-18",
                "symbol": "NVDA",
                "strategy": "cascade_overreaction",
                "return_1d_pct": -5.2,
                "return_5d_pct": -7.1,
                "rsi_14": 28.0,
                "volatility_20d_annualized": 0.42,
                "relative_volume": 2.1,
                "bollinger_position": -0.75,
                "distance_from_ma50_pct": -5.0,
                "cascade_score": -2.8,
                "vix_level": 21.0,
                "vix_5d_change": 2.5,
                "days_since_earnings": 25,
                "earnings_within_7d": False,
                "recent_news": ["Semiconductor sector declines following macro interest rate comments"]
            }
        }
    ]

    results = []

    for sc in scenarios:
        name = sc["name"]
        st = sc["state"]
        exp = sc["expected_verdict"]

        print(f"--- Running Scenario: {name} ---")

        # 1. TypeSafe Jev
        jev_res = jev_agent.evaluate_state(st)
        jev_verdict = "VETOED" if jev_res.get("veto_trade") else "APPROVED"
        jev_latency = jev_res.get("latency_ms", 0.0)
        jev_type = jev_res.get("anomaly_type")

        # 2. Snowflake Cortex AI
        cortex_res = cortex_agent.evaluate_state(st)
        cortex_verdict = "VETOED" if cortex_res.get("veto_trade") else "APPROVED"
        cortex_latency = cortex_res.get("latency_ms", 0.0)
        cortex_type = cortex_res.get("anomaly_type")

        print(f"  TypeSafe Jev:     Verdict: {jev_verdict:8s} | Anomaly: {jev_type:15s} | Latency: {jev_latency:6.1f}ms | Rev P: {jev_res.get('mean_reversion_prob',0)*100:2.0f}%")
        print(f"  Snowflake Cortex: Verdict: {cortex_verdict:8s} | Anomaly: {cortex_type:15s} | Latency: {cortex_latency:6.1f}ms | Rev P: {cortex_res.get('mean_reversion_prob',0)*100:2.0f}%")
        print(f"  Expected:         {exp}\n")

        results.append({
            "Scenario": name,
            "Expected": exp,
            "Jev_Verdict": jev_verdict,
            "Jev_Type": jev_type,
            "Jev_Latency_ms": jev_latency,
            "Jev_Rev_Prob": jev_res.get("mean_reversion_prob"),
            "Cortex_Verdict": cortex_verdict,
            "Cortex_Type": cortex_type,
            "Cortex_Latency_ms": cortex_latency,
            "Cortex_Rev_Prob": cortex_res.get("mean_reversion_prob")
        })

    df_res = pd.DataFrame(results)

    # Summary Statistics
    jev_accuracy = (df_res["Jev_Verdict"] == df_res["Expected"]).mean() * 100
    cortex_accuracy = (df_res["Cortex_Verdict"] == df_res["Expected"]).mean() * 100
    jev_avg_lat = df_res["Jev_Latency_ms"].mean()
    cortex_avg_lat = df_res["Cortex_Latency_ms"].mean()

    # Cost Estimates (per 1,000 evaluations)
    # Jev: ~832 tokens/call = ~$0.002 / call = ~$2.00 / 1,000 calls
    # Snowflake Cortex: ~0.00005 credits / call = ~$0.15 / 1,000 calls
    jev_cost_1k = 2.00
    cortex_cost_1k = 0.15

    print("==================================================================")
    print("                    FINAL BENCHMARK SCORECARD                     ")
    print("==================================================================")
    print(f"Metric                  TypeSafe Jev (1.13.0)   Snowflake Cortex AI")
    print(f"------------------------------------------------------------------")
    print(f"Veto Accuracy:          {jev_accuracy:6.1f}%                 {cortex_accuracy:6.1f}%")
    print(f"Average Latency:        {jev_avg_lat:6.1f} ms               {cortex_avg_lat:6.1f} ms")
    print(f"Cost per 1k Calls:      ${jev_cost_1k:5.2f}                  ${cortex_cost_1k:5.2f}")
    print(f"Output Structure:       Noul / Probabilities    JSON / Heuristics")
    print(f"Multi-Question Parallel:YES (Native SystemOne)   Sequential / Structured")
    print("==================================================================\n")

    # Save benchmark report to data/reports/
    report_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "reports", "jev_vs_cortex_benchmark.txt")
    with open(report_file, "w") as f:
        f.write("=== HEAD-TO-HEAD BENCHMARK: TYPESAFE JEV vs. SNOWFLAKE CORTEX ===\n\n")
        f.write(df_res.to_string(index=False))
        f.write("\n\n")
        f.write(f"Jev Veto Accuracy:       {jev_accuracy:.1f}%\n")
        f.write(f"Cortex Veto Accuracy:    {cortex_accuracy:.1f}%\n")
        f.write(f"Jev Avg Latency:         {jev_avg_lat:.1f} ms\n")
        f.write(f"Cortex Avg Latency:      {cortex_avg_lat:.1f} ms\n")
        f.write(f"Jev Cost / 1k Calls:     ${jev_cost_1k:.2f}\n")
        f.write(f"Cortex Cost / 1k Calls:  ${cortex_cost_1k:.2f}\n")

if __name__ == "__main__":
    run_benchmark()
