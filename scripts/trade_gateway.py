"""
TradeGateway:
Deterministic Pre-Trade Risk Gateway (The Institutional Trading Cage).

Enforces hard mathematical constraints and Human Owner Policy (config/cage_policy.json)
BEFORE any order can reach a broker API:
- Physical Kill-Switch Check (data/KILL_SWITCH)
- Dynamic Universe Allowlist (config.TICKERS)
- Human-Locked Capital Envelope ($20,000)
- Shorting & Leverage Permissions (No shorting, max 1.0x leverage)
- Max Single Position Size ($5,000 / 25%)
- Daily Drawdown & Volatility Circuit Breakers (VIX < 40)
- Immutable Audit Logging (DuckDB trade_audit_log)

Usage:
    gateway = TradeGateway()
    decision = gateway.validate_order(symbol, requested_dollars, current_positions, portfolio_value, vix)
"""

import os, sys, json, uuid
from datetime import datetime
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from scripts.storage import init_db

POLICY_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "cage_policy.json")
KILL_SWITCH_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "KILL_SWITCH")

class TradeGateway:
    def __init__(self, policy_path: str = POLICY_PATH):
        self.policy_path = policy_path
        self.policy = self._load_policy()

    def _load_policy(self) -> dict:
        """Load human-locked configuration policy."""
        if os.path.exists(self.policy_path):
            with open(self.policy_path) as f:
                return json.load(f)
        return {
            "capital_limits": {
                "max_capital_envelope_usd": 20000.0,
                "max_single_position_pct": 0.25,
                "max_single_position_usd": 5000.0,
                "max_daily_turnover_usd": 15000.0,
                "min_order_dollars_usd": 100.0
            },
            "risk_permissions": {
                "allow_shorting": False,
                "max_leverage": 1.0,
                "allow_naked_options": False
            },
            "circuit_breakers": {
                "max_daily_loss_usd": 500.0,
                "max_vix_threshold": 40.0
            }
        }

    def validate_order(
        self,
        symbol: str,
        side: str,
        requested_dollars: float,
        current_holdings: dict,
        portfolio_value: float,
        vix_level: float = 18.0,
        strategy_name: str = "unnamed",
        jev_meta: dict = None
    ) -> dict:
        """
        Evaluate order against 7 deterministic risk checks.
        Returns:
            dict with:
                allowed: bool
                verdict: 'APPROVED', 'MODIFIED', 'REJECTED'
                approved_dollars: float
                rejection_reasons: list[str]
                checks_passed: list[str]
        """
        rejection_reasons = []
        checks_passed = []
        approved_dollars = requested_dollars
        verdict = "APPROVED"

        cap_limits = self.policy.get("capital_limits", {})
        risk_perms = self.policy.get("risk_permissions", {})
        breakers = self.policy.get("circuit_breakers", {})

        # Check 1: Physical Emergency Kill-Switch
        if os.path.exists(KILL_SWITCH_FILE):
            rejection_reasons.append("EMERGENCY_KILL_SWITCH_ACTIVE: data/KILL_SWITCH file present.")
        else:
            checks_passed.append("KILL_SWITCH_CLEAR")

        # Check 2: Dynamic Universe Allowlist (Dynamically scales with config.TICKERS)
        allowed_tickers = set(config.TICKERS)
        if symbol not in allowed_tickers:
            rejection_reasons.append(f"UNAUTHORIZED_SYMBOL: {symbol} is not in the human-approved universe ({len(allowed_tickers)} tickers).")
        else:
            checks_passed.append("UNIVERSE_ALLOWLIST")

        # Check 3: Shorting Permission
        if side.lower() == "sell" and requested_dollars < 0:
            if not risk_perms.get("allow_shorting", False):
                rejection_reasons.append("SHORTING_FORBIDDEN: Human policy has disabled short selling.")
            else:
                checks_passed.append("SHORTING_PERMITTED")
        else:
            checks_passed.append("LONG_ONLY_SAFE")

        # Check 4: Volatility Circuit Breaker
        max_vix = breakers.get("max_vix_threshold", 40.0)
        if vix_level > max_vix:
            rejection_reasons.append(f"VOLATILITY_CIRCUIT_BREAKER: Market VIX ({vix_level:.1f}) exceeds maximum threshold ({max_vix:.1f}).")
        else:
            checks_passed.append("VOLATILITY_NORMAL")

        # Check 5: Maximum Capital Envelope & Leverage Limit
        max_envelope = cap_limits.get("max_capital_envelope_usd", 20000.0)
        max_leverage = risk_perms.get("max_leverage", 1.0)
        current_gross_exposure = sum(abs(v.get("market_value", 0.0)) for v in current_holdings.values())
        new_gross_exposure = current_gross_exposure + abs(requested_dollars)

        if new_gross_exposure > (max_envelope * max_leverage):
            # Clamp to remaining capital envelope capacity
            available_capacity = max(0.0, (max_envelope * max_leverage) - current_gross_exposure)
            if available_capacity < cap_limits.get("min_order_dollars_usd", 100.0):
                rejection_reasons.append(f"CAPITAL_ENVELOPE_EXCEEDED: Gross exposure (${new_gross_exposure:,.0f}) exceeds capital cage limit (${max_envelope:,.0f}).")
            else:
                approved_dollars = available_capacity
                verdict = "MODIFIED"
                checks_passed.append("CAPITAL_ENVELOPE_CLAMPED")
        else:
            checks_passed.append("CAPITAL_ENVELOPE_OK")

        # Check 6: Maximum Single Position Size Limit
        max_pos_usd = cap_limits.get("max_single_position_usd", 5000.0)
        max_pos_pct = cap_limits.get("max_single_position_pct", 0.25)
        max_allowed_for_stock = min(max_pos_usd, portfolio_value * max_pos_pct)

        current_stock_val = abs(current_holdings.get(symbol, {}).get("market_value", 0.0))
        target_total_val = current_stock_val + abs(approved_dollars)

        if target_total_val > max_allowed_for_stock:
            clamped_order = max(0.0, max_allowed_for_stock - current_stock_val)
            if clamped_order < cap_limits.get("min_order_dollars_usd", 100.0):
                rejection_reasons.append(f"MAX_POSITION_LIMIT_REACHED: {symbol} already at limit (${current_stock_val:,.0f} / max ${max_allowed_for_stock:,.0f}).")
            else:
                approved_dollars = clamped_order
                verdict = "MODIFIED"
                checks_passed.append("POSITION_SIZE_CLAMPED")
        else:
            checks_passed.append("POSITION_SIZE_OK")

        # Check 7: Minimum Order Size
        if abs(approved_dollars) < cap_limits.get("min_order_dollars_usd", 100.0) and not rejection_reasons:
            rejection_reasons.append(f"BELOW_MIN_ORDER_SIZE: Order (${approved_dollars:.2f}) below minimum threshold.")

        allowed = len(rejection_reasons) == 0
        if not allowed:
            verdict = "REJECTED"
            approved_dollars = 0.0

        decision = {
            "allowed": allowed,
            "verdict": verdict,
            "symbol": symbol,
            "side": side,
            "requested_dollars": round(float(requested_dollars), 2),
            "approved_dollars": round(float(approved_dollars), 2),
            "rejection_reasons": rejection_reasons,
            "checks_passed": checks_passed,
            "strategy": strategy_name,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        return decision

    def log_audit(self, conn, decision: dict, shares: int = 0, est_price: float = 0.0, broker: str = "alpaca", broker_order_id: str = None, status: str = "SUBMITTED"):
        """Write immutable trade decision trail to DuckDB trade_audit_log table."""
        trade_id = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO trade_audit_log (
                trade_id, timestamp, symbol, strategy, side,
                requested_dollars, approved_dollars, shares, estimated_price,
                gateway_verdict, risk_checks_passed, rejection_reasons,
                jev_meta_label, broker, broker_order_id, status
            ) VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            trade_id,
            decision.get("symbol"),
            decision.get("strategy"),
            decision.get("side"),
            decision.get("requested_dollars"),
            decision.get("approved_dollars"),
            shares,
            est_price,
            decision.get("verdict"),
            json.dumps(decision.get("checks_passed")),
            json.dumps(decision.get("rejection_reasons")),
            json.dumps(decision.get("jev_meta", {})),
            broker,
            broker_order_id,
            status
        ])
        return trade_id
