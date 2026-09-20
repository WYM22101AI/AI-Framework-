"""
Test Suite: Institutional Trading Cage & Deterministic Risk Gateway
Validates all 7 human-governed constraints and broker adapter operations.

Usage:
    python scripts/test_trade_gateway.py
"""

import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from scripts.trade_gateway import TradeGateway, KILL_SWITCH_FILE
from scripts.broker_adapter import get_broker_adapter
from scripts.storage import init_db

def run_tests():
    print("==================================================================", flush=True)
    print("  TESTING INSTITUTIONAL TRADING CAGE & DETERMINISTIC RISK GATEWAY ", flush=True)
    print("==================================================================\n", flush=True)

    gateway = TradeGateway()

    # 1. Normal Approved Order
    res1 = gateway.validate_order(
        symbol="AMZN",
        side="buy",
        requested_dollars=3500.0,
        current_holdings={},
        portfolio_value=20000.0,
        vix_level=18.5
    )
    print("Test 1: Normal Approved Order ($3,500 AMZN)")
    print(f"  Verdict:  {res1['verdict']} | Approved: ${res1['approved_dollars']:,}")
    assert res1['allowed'] and res1['approved_dollars'] == 3500.0, "Expected order to be APPROVED"
    print("  [PASS]\n")

    # 2. Position Size Clamping (Oversized $12,000 order clamped to $5,000 max)
    res2 = gateway.validate_order(
        symbol="NVDA",
        side="buy",
        requested_dollars=12000.0,
        current_holdings={},
        portfolio_value=20000.0,
        vix_level=18.5
    )
    print("Test 2: Oversized Order Clamping ($12,000 requested -> $5,000 limit)")
    print(f"  Verdict:  {res2['verdict']} | Approved: ${res2['approved_dollars']:,}")
    assert res2['verdict'] == "MODIFIED" and res2['approved_dollars'] == 5000.0, "Expected order to be CLAMPED to $5,000"
    print("  [PASS]\n")

    # 3. Short Selling Blocked
    res3 = gateway.validate_order(
        symbol="TSLA",
        side="sell",
        requested_dollars=-3000.0,
        current_holdings={},
        portfolio_value=20000.0,
        vix_level=18.5
    )
    print("Test 3: Short Selling Permission Blocked")
    print(f"  Verdict:  {res3['verdict']} | Reasons: {res3['rejection_reasons']}")
    assert not res3['allowed'] and "SHORTING_FORBIDDEN" in res3['rejection_reasons'][0], "Expected shorting to be REJECTED"
    print("  [PASS]\n")

    # 4. Unauthorized Symbol Blocked
    res4 = gateway.validate_order(
        symbol="DOGECOIN",
        side="buy",
        requested_dollars=1000.0,
        current_holdings={},
        portfolio_value=20000.0,
        vix_level=18.5
    )
    print("Test 4: Non-Universe Symbol Blocked (DOGECOIN)")
    print(f"  Verdict:  {res4['verdict']} | Reasons: {res4['rejection_reasons']}")
    assert not res4['allowed'] and "UNAUTHORIZED_SYMBOL" in res4['rejection_reasons'][0], "Expected non-universe to be REJECTED"
    print("  [PASS]\n")

    # 5. Volatility Circuit Breaker (VIX > 40)
    res5 = gateway.validate_order(
        symbol="CAT",
        side="buy",
        requested_dollars=2000.0,
        current_holdings={},
        portfolio_value=20000.0,
        vix_level=46.5
    )
    print("Test 5: Volatility Circuit Breaker Triggered (VIX = 46.5)")
    print(f"  Verdict:  {res5['verdict']} | Reasons: {res5['rejection_reasons']}")
    assert not res5['allowed'] and "VOLATILITY_CIRCUIT_BREAKER" in res5['rejection_reasons'][0], "Expected VIX breaker to REJECT"
    print("  [PASS]\n")

    # 6. Physical Emergency Kill-Switch Activation
    try:
        with open(KILL_SWITCH_FILE, "w") as f:
            f.write("EMERGENCY_HALT_BY_HUMAN")

        res6 = gateway.validate_order(
            symbol="AMZN",
            side="buy",
            requested_dollars=2000.0,
            current_holdings={},
            portfolio_value=20000.0,
            vix_level=18.0
        )
        print("Test 6: Emergency Physical Kill-Switch (data/KILL_SWITCH active)")
        print(f"  Verdict:  {res6['verdict']} | Reasons: {res6['rejection_reasons']}")
        assert not res6['allowed'] and "EMERGENCY_KILL_SWITCH_ACTIVE" in res6['rejection_reasons'][0], "Expected kill-switch to REJECT"
        print("  [PASS]\n")
    finally:
        if os.path.exists(KILL_SWITCH_FILE):
            os.remove(KILL_SWITCH_FILE)

    # 7. Broker Adapter Tests (Alpaca, IBKR, Simulation)
    print("Test 7: Multi-Broker Adapter Abstraction")
    sim_broker = get_broker_adapter("simulated")
    sim_acct = sim_broker.get_account()
    print(f"  Simulated Broker Account:  ${sim_acct['portfolio_value']:,.2f} ({sim_acct['status']})")
    assert sim_acct['portfolio_value'] == 20000.0

    ibkr_broker = get_broker_adapter("ibkr")
    ibkr_acct = ibkr_broker.get_account()
    print(f"  Interactive Brokers (IBKR): ${ibkr_acct['portfolio_value']:,.2f} ({ibkr_acct['status']})")
    assert ibkr_acct['broker'] == "ibkr"

    alpaca_broker = get_broker_adapter("alpaca")
    alpaca_acct = alpaca_broker.get_account()
    print(f"  Alpaca Live Paper Account:  ${alpaca_acct['portfolio_value']:,.2f} ({alpaca_acct['status']})")
    assert alpaca_acct['broker'] == "alpaca"
    print("  [PASS]\n")

    # 8. Immutable DuckDB Audit Logging
    print("Test 8: Immutable DuckDB `trade_audit_log` Table Persistence")
    conn = init_db(config.DB_PATH)
    trade_id = gateway.log_audit(
        conn=conn,
        decision=res1,
        shares=18,
        est_price=186.5,
        broker="alpaca",
        broker_order_id="TEST-ALPACA-001",
        status="TEST_VERIFIED"
    )

    df_audit = conn.execute(f"SELECT trade_id, symbol, side, requested_dollars, approved_dollars, gateway_verdict, broker, status FROM trade_audit_log WHERE trade_id = '{trade_id}'").fetchdf()
    conn.close()

    print(df_audit.to_string(index=False))
    assert len(df_audit) == 1, "Expected audit log record in DuckDB"
    print("\n ALL 8 TRADING CAGE & RISK GATEWAY TESTS PASSED (100% SUCCESS)!")

if __name__ == "__main__":
    run_tests()
