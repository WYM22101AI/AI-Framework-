"""
Paper Trading Module (With Institutional Trading Cage Protection):
Executes the approved multi-sector production strategies on Alpaca or IBKR.

All orders must pass through the deterministic TradeGateway (The Cage)
before reaching any broker API.
"""

import sys, os
from datetime import datetime
import pandas as pd
import duckdb

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
import scripts.signal_generator as sg
from scripts.storage import init_db
from scripts.trade_gateway import TradeGateway
from scripts.broker_adapter import get_broker_adapter

APPROVED_STOCKS = ["AMZN", "CAT", "NVDA", "V", "COST"]

def get_current_signals(conn) -> dict:
    """Generate today's signals for the promoted production portfolio."""
    signals = {}
    strat_map = {
        "AMZN": sg.strategy_mr_vix_tuned,
        "CAT": sg.strategy_momentum_regime,
        "NVDA": sg.strategy_mr_vix_tuned,
        "V": sg.strategy_mr_vix_tuned,
        "COST": sg.strategy_mean_reversion_regime,
    }

    for symbol in APPROVED_STOCKS:
        try:
            fn = strat_map.get(symbol, sg.strategy_mr_vix_tuned)
            sig = fn(conn, symbol)
            if sig is not None and not sig.empty:
                latest = sig.iloc[-1]
                latest_date = sig.index[-1]
                val = 1 if latest else 0
                signals[symbol] = {
                    "signal": val,
                    "direction": "LONG" if val == 1 else "FLAT",
                    "date": str(latest_date),
                }
            else:
                signals[symbol] = {"signal": 0, "direction": "NO_DATA", "date": "unknown"}
        except Exception as e:
            signals[symbol] = {"signal": 0, "direction": "ERROR", "date": str(e)}

    return signals


def compute_position_sizes(signals: dict, portfolio_value: float) -> dict:
    """Compute dollar targets for approved stocks."""
    weights = {
        "AMZN": 0.25,
        "CAT": 0.20,
        "NVDA": 0.20,
        "V": 0.15,
        "COST": 0.20,
    }

    positions = {}
    for sym, sig in signals.items():
        if sig["signal"] == 1:
            w = weights.get(sym, 0.20)
            positions[sym] = portfolio_value * w
        else:
            positions[sym] = 0.0

    return positions


def run_paper_trading(execute: bool = False, broker_name: str = "alpaca"):
    print(f"=== Paper Trader (Trading Cage Protected): {datetime.now().strftime('%Y-%m-%d %H:%M')} ===", flush=True)
    print(f"Mode: {'LIVE EXECUTION' if execute else 'DRY RUN (no orders submitted)'}", flush=True)
    print(f"Broker: {broker_name.upper()}", flush=True)
    print(f"Approved Universe: {APPROVED_STOCKS}\n", flush=True)

    # 1. Connect Broker & Gateway
    broker = get_broker_adapter(broker_name)
    gateway = TradeGateway()

    acct = broker.get_account()
    portfolio_val = acct.get("portfolio_value", 20000.0)
    print(f"Account Balance:    ${portfolio_val:,.2f}")
    print(f"Available Cash:     ${acct.get('cash', 0.0):,.2f}")
    print(f"Buying Power:       ${acct.get('buying_power', 0.0):,.2f}")

    # 2. Generate Signals
    conn = init_db(config.DB_PATH)
    signals = get_current_signals(conn)

    print("\n--- Strategy Signals ---")
    for sym, sig in signals.items():
        print(f"  {sym:5s}: {sig['direction']:6s} (signal={sig['signal']}, as of {sig['date']})")

    # 3. Position Sizing
    targets = compute_position_sizes(signals, portfolio_val)
    holdings = broker.get_positions()

    print("\n--- Target vs Current Holdings ---")
    for sym in APPROVED_STOCKS:
        tgt = targets.get(sym, 0.0)
        curr = holdings.get(sym, {}).get("market_value", 0.0)
        print(f"  {sym:5s}: Target: ${tgt:8,.0f} | Current: ${curr:8,.0f} | Diff: ${tgt - curr:8,.0f}")

    # 4. Generate Orders & Validate Through Trading Cage Gateway
    print("\n--- Trading Cage Gateway Validation ---")
    orders_to_submit = []

    # Get latest VIX
    vix_row = conn.execute("SELECT vix FROM daily_features ORDER BY date DESC LIMIT 1").fetchone()
    vix_level = float(vix_row[0]) if vix_row and vix_row[0] else 18.0

    for sym, target_dollars in targets.items():
        curr_val = holdings.get(sym, {}).get("market_value", 0.0)
        diff = target_dollars - curr_val

        if abs(diff) < 100:  # Skip trivial adjustments
            continue

        side = "buy" if diff > 0 else "sell"

        # Pass through the Deterministic Risk Gateway
        decision = gateway.validate_order(
            symbol=sym,
            side=side,
            requested_dollars=abs(diff),
            current_holdings=holdings,
            portfolio_value=portfolio_val,
            vix_level=vix_level,
            strategy_name=f"{sym}_production_strategy"
        )

        status_tag = f"[{decision['verdict']}]"
        print(f"  {sym:5s} {side.upper():4s} ${abs(diff):7,.0f} -> {status_tag:10s} Approved: ${decision['approved_dollars']:7,.0f}")
        if decision["rejection_reasons"]:
            print(f"       Rejection Reasons: {', '.join(decision['rejection_reasons'])}")

        if decision["allowed"] and decision["approved_dollars"] >= 100:
            # Estimate shares
            price_row = conn.execute(f"SELECT close FROM daily_bars WHERE symbol = '{sym}' ORDER BY timestamp DESC LIMIT 1").fetchone()
            price = float(price_row[0]) if price_row else 100.0
            shares = int(decision["approved_dollars"] / price)

            if shares > 0:
                orders_to_submit.append({
                    "symbol": sym,
                    "side": side,
                    "qty": shares,
                    "price_est": price,
                    "decision": decision
                })

    # 5. Order Execution & Audit Logging
    print("\n--- Execution & Audit Logging ---")
    if not orders_to_submit:
        print("  No rebalancing orders required today (portfolio aligned).")
    else:
        for item in orders_to_submit:
            sym = item["symbol"]
            qty = item["qty"]
            side = item["side"]
            dec = item["decision"]

            if execute:
                order_res = broker.submit_order(symbol=sym, qty=qty, side=side)
                order_id = order_res.get("order_id", "ERROR")
                print(f"  EXECUTED: {side.upper()} {qty} {sym} -> Order ID: {order_id} ({order_res.get('status')})")
                gateway.log_audit(conn, dec, shares=qty, est_price=item["price_est"], broker=broker_name, broker_order_id=order_id, status="SUBMITTED")
            else:
                sim_id = f"SIM-{sym}-{datetime.now().strftime('%H%M%S')}"
                print(f"  SIMULATED: {side.upper()} {qty} {sym} @ ~${item['price_est']:.2f} (Paper Trade Logged)")
                gateway.log_audit(conn, dec, shares=qty, est_price=item["price_est"], broker=broker_name, broker_order_id=sim_id, status="SIMULATED")

    conn.close()
    print(f"\nAll decisions logged to DuckDB `trade_audit_log` table.", flush=True)

if __name__ == "__main__":
    is_exec = "--execute" in sys.argv
    run_paper_trading(execute=is_exec)
