"""
Paper Trader: connect surviving strategies to Alpaca paper trading.
Generates target positions from signals and submits orders.

Usage:
    python scripts/paper_trader.py              # Dry run (show orders, don't submit)
    python scripts/paper_trader.py --execute    # Actually submit orders
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import duckdb
import pandas as pd
import numpy as np
from datetime import datetime
import alpaca_trade_api as tradeapi
import config
from scripts.storage import init_db, upsert_generic
from scripts.signal_generator import strategy_mr_vix_tuned


# Stocks approved for paper trading (passed Skeptic or strong positive OOS)
APPROVED_STOCKS = ["AMZN", "NVDA"]

# Position sizing
MAX_POSITION_PCT = 0.25       # Max 25% of portfolio per stock
TOTAL_EXPOSURE_PCT = 0.50     # Max 50% total invested (keep cash buffer)
PORTFOLIO_VALUE = 100_000     # Paper trading starting capital


def get_current_signals(conn) -> dict:
    """Generate today's signals for approved stocks."""
    signals = {}
    for symbol in APPROVED_STOCKS:
        signal = strategy_mr_vix_tuned(conn, symbol)
        if not signal.empty:
            latest_date = signal.index.max()
            latest_signal = int(signal.iloc[-1])
            signals[symbol] = {
                "signal": latest_signal,
                "date": latest_date,
                "direction": "LONG" if latest_signal == 1 else "SHORT" if latest_signal == -1 else "FLAT",
            }
    return signals


def compute_position_sizes(signals: dict, portfolio_value: float) -> dict:
    """
    Compute dollar position sizes.
    - Each stock gets equal weight when signal is active
    - Max 25% per stock, max 50% total
    """
    active = {sym: sig for sym, sig in signals.items() if sig["signal"] != 0}

    if not active:
        return {sym: 0 for sym in signals}

    # Equal weight among active positions
    n_active = len(active)
    per_stock = min(
        portfolio_value * MAX_POSITION_PCT,
        portfolio_value * TOTAL_EXPOSURE_PCT / n_active,
    )

    positions = {}
    for sym, sig in signals.items():
        if sig["signal"] == 0:
            positions[sym] = 0
        else:
            positions[sym] = per_stock * sig["signal"]  # Negative for short

    return positions


def get_current_holdings(api) -> dict:
    """Get current paper trading positions."""
    try:
        positions = api.list_positions()
        return {p.symbol: {"qty": int(p.qty), "side": p.side, "market_value": float(p.market_value)} for p in positions}
    except Exception as e:
        print(f"  Error getting positions: {e}")
        return {}


def compute_orders(target_positions: dict, current_holdings: dict, api) -> list:
    """
    Compare target vs current positions and generate orders.
    Returns list of order dicts.
    """
    orders = []

    for symbol, target_dollars in target_positions.items():
        current = current_holdings.get(symbol, {"qty": 0, "market_value": 0})
        current_value = current["market_value"]

        diff = target_dollars - current_value

        if abs(diff) < 500:  # Skip tiny adjustments
            continue

        # Get current price for share calculation
        try:
            quote = api.get_latest_trade(symbol)
            price = quote.price
        except Exception:
            price = None

        if price is None or price <= 0:
            continue

        shares = int(abs(diff) / price)
        if shares == 0:
            continue

        side = "buy" if diff > 0 else "sell"

        orders.append({
            "symbol": symbol,
            "side": side,
            "qty": shares,
            "type": "market",
            "time_in_force": "day",
            "target_dollars": target_dollars,
            "current_value": current_value,
            "diff": diff,
            "price_estimate": price,
        })

    return orders


def log_trades(conn, orders: list, signals: dict, executed: bool):
    """Log trade decisions to DuckDB."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trade_log (
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            symbol TEXT,
            signal_direction TEXT,
            order_side TEXT,
            qty INT,
            price_estimate DOUBLE,
            target_dollars DOUBLE,
            executed BOOLEAN,
            notes TEXT
        )
    """)

    for order in orders:
        sig = signals.get(order["symbol"], {})
        conn.execute("""
            INSERT INTO trade_log (symbol, signal_direction, order_side, qty, price_estimate, target_dollars, executed, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            order["symbol"],
            sig.get("direction", "UNKNOWN"),
            order["side"],
            order["qty"],
            order["price_estimate"],
            order["target_dollars"],
            executed,
            f"mr_vix_tuned signal on {sig.get('date', 'unknown')}",
        ])


def main():
    execute = "--execute" in sys.argv

    print(f"=== Paper Trader: {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    print(f"Mode: {'LIVE EXECUTION' if execute else 'DRY RUN (no orders submitted)'}")
    print(f"Approved stocks: {APPROVED_STOCKS}")
    print(f"Portfolio: ${PORTFOLIO_VALUE:,.0f}")
    print()

    # Connect
    conn = duckdb.connect(config.DB_PATH, read_only=True)
    api = tradeapi.REST(config.API_KEY, config.API_SECRET, config.BASE_URL, api_version="v2")

    # Get account info
    try:
        account = api.get_account()
        actual_portfolio = float(account.portfolio_value)
        print(f"Paper account value: ${actual_portfolio:,.2f}")
        print(f"Buying power: ${float(account.buying_power):,.2f}")
    except Exception as e:
        print(f"Could not get account info: {e}")
        actual_portfolio = PORTFOLIO_VALUE

    # Generate signals
    print("\n--- Signals ---")
    signals = get_current_signals(conn)
    conn.close()

    for sym, sig in signals.items():
        print(f"  {sym}: {sig['direction']} (signal={sig['signal']}, date={sig['date']})")

    # Position sizing
    positions = compute_position_sizes(signals, actual_portfolio)
    print("\n--- Target Positions ---")
    for sym, dollars in positions.items():
        if dollars != 0:
            print(f"  {sym}: ${dollars:+,.0f}")
        else:
            print(f"  {sym}: FLAT (no position)")

    # Current holdings
    print("\n--- Current Holdings ---")
    holdings = get_current_holdings(api)
    if holdings:
        for sym, h in holdings.items():
            print(f"  {sym}: {h['qty']} shares (${h['market_value']:,.2f})")
    else:
        print("  No positions")

    # Compute orders
    orders = compute_orders(positions, holdings, api)

    print("\n--- Orders ---")
    if not orders:
        print("  No orders needed (positions match targets)")
    else:
        for o in orders:
            print(f"  {o['side'].upper()} {o['qty']} {o['symbol']} @ ~${o['price_estimate']:.2f} (target: ${o['target_dollars']:+,.0f})")

    # Execute or log
    if execute and orders:
        print("\n--- Executing ---")
        for o in orders:
            try:
                api.submit_order(
                    symbol=o["symbol"],
                    qty=o["qty"],
                    side=o["side"],
                    type=o["type"],
                    time_in_force=o["time_in_force"],
                )
                print(f"  SUBMITTED: {o['side']} {o['qty']} {o['symbol']}")
            except Exception as e:
                print(f"  FAILED: {o['symbol']} - {e}")

    # Log to DuckDB
    log_conn = init_db(config.DB_PATH)
    log_trades(log_conn, orders, signals, executed=execute)
    log_conn.close()
    print(f"\nLogged {len(orders)} orders to trade_log table.")

    print("\nDone.")


if __name__ == "__main__":
    main()
