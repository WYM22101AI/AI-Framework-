"""
Test Meta-Labeler Agent:
Validates Layer 2.5 decision gate against 4 distinct test scenarios:
1. Clean technical oversold bounce -> APPROVED
2. Negative news crisis (falling knife) -> VETOED
3. Data glitch / split artifact -> VETOED
4. Earnings binary risk -> VETOED

Usage:
    python scripts/test_meta_labeler.py
"""
import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from agents.meta_labeler import MetaLabelerAgent
from scripts.storage import init_db

def run_tests():
    print("===========================================================", flush=True)
    print("  TESTING CORTEX META-LABELER AGENT (LAYER 2.5 GATE)      ", flush=True)
    print("===========================================================\n", flush=True)

    agent = MetaLabelerAgent()

    # Scenario 1: Clean Technical Bounce (e.g. AMZN during market panic)
    state_clean = {
        "as_of": "2026-09-18",
        "symbol": "AMZN",
        "strategy": "vix_regime_mean_reversion",
        "return_1d_pct": -4.8,
        "return_5d_pct": -7.2,
        "rsi_14": 26.5,
        "volatility_20d_annualized": 0.28,
        "relative_volume": 1.65,
        "bollinger_position": -0.85,
        "distance_from_ma50_pct": -6.5,
        "cascade_score": -2.4,
        "vix_level": 24.5,
        "vix_5d_change": 4.2,
        "days_since_earnings": 45,
        "earnings_within_7d": False,
        "recent_news": ["AMZN expands cloud AI infrastructure in Europe", "Tech sector pulls back on rate concerns"]
    }

    res1 = agent.evaluate_state(state_clean)
    print("1. Scenario A: Clean Technical Oversold Setup")
    print(f"   Verdict:       {'VETOED' if res1['veto_trade'] else 'APPROVED'}")
    print(f"   Anomaly Type:  {res1['anomaly_type']}")
    print(f"   Reversion P:   {res1['mean_reversion_prob']*100:.0f}%")
    print(f"   Quality Weight:{res1['quality_weight']:.2f}")
    print(f"   Reasoning:     {res1['reasoning']}")
    assert not res1['veto_trade'], "Expected clean technical setup to be APPROVED"
    print("   [PASS]\n")

    # Scenario 2: Negative News Crisis (e.g. Fraud or Regulatory probe)
    state_crisis = {
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

    res2 = agent.evaluate_state(state_crisis)
    print("2. Scenario B: Company Crisis / Falling Knife")
    print(f"   Verdict:       {'VETOED' if res2['veto_trade'] else 'APPROVED'}")
    print(f"   Anomaly Type:  {res2['anomaly_type']}")
    print(f"   Continuation P:{res2['continuation_prob']*100:.0f}%")
    print(f"   Reasoning:     {res2['reasoning']}")
    assert res2['veto_trade'], "Expected crisis to be VETOED"
    print("   [PASS]\n")

    # Scenario 3: Data Error / Split Glitch
    state_glitch = {
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

    res3 = agent.evaluate_state(state_glitch)
    print("3. Scenario C: Data Error / Unadjusted Split Artifact")
    print(f"   Verdict:       {'VETOED' if res3['veto_trade'] else 'APPROVED'}")
    print(f"   Anomaly Type:  {res3['anomaly_type']}")
    print(f"   Data Error:    {res3['possible_data_error']}")
    print(f"   Reasoning:     {res3['reasoning']}")
    assert res3['veto_trade'] and res3['possible_data_error'], "Expected data error to be VETOED"
    print("   [PASS]\n")

    # Scenario 4: Earnings Risk
    state_earnings = {
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

    res4 = agent.evaluate_state(state_earnings)
    print("4. Scenario D: Earnings Binary Event Risk")
    print(f"   Verdict:       {'VETOED' if res4['veto_trade'] else 'APPROVED'}")
    print(f"   Reasoning:     {res4['reasoning']}")
    assert res4['veto_trade'], "Expected earnings risk to be VETOED"
    print("   [PASS]\n")

    # 5. Live DuckDB persistence test
    conn = init_db(config.DB_PATH)
    agent.store_evaluation(conn, "AMZN", "2026-09-18", "vix_regime_mean_reversion", res1)
    stored = conn.execute("SELECT * FROM meta_labels WHERE symbol = 'AMZN'").fetchdf()
    conn.close()

    print("5. Live DuckDB `meta_labels` Table Persistence:")
    print(stored[['symbol', 'date', 'strategy', 'anomaly_type', 'veto_trade', 'quality_weight', 'model_engine']].to_string(index=False))
    print("\n ALL 5 META-LABELER UNIT TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
