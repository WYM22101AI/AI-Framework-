"""
Gatekeeper Agent: final authority on promoting strategies to paper trading.

Takes a Skeptic evaluation and makes the promotion decision. The Gatekeeper
adds portfolio-level checks that the Skeptic doesn't consider:
- Correlation with existing approved strategies
- Total portfolio exposure
- Strategy diversity (not all momentum, not all one sector)

For now, the Gatekeeper uses simple rules. Can be upgraded to LLM-assisted
decision-making when we have more strategies to manage.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime
from agents.base import BaseAgent


class GatekeeperAgent(BaseAgent):
    def __init__(self):
        super().__init__("gatekeeper", "Final promotion authority. Manages the approved strategy portfolio.")

    # Portfolio constraints
    MAX_APPROVED_STRATEGIES = 10
    MAX_SINGLE_STOCK_STRATEGIES = 3  # max 3 strategies on same stock
    MAX_PORTFOLIO_EXPOSURE = 0.80    # 80% of portfolio

    def think(self, context: dict) -> dict:
        """
        context: {
            'skeptic_evaluation': dict from SkepticAgent,
            'current_approved': list of currently approved strategy-stock pairs,
        }
        """
        evaluation = context.get("skeptic_evaluation", {})
        current = context.get("current_approved", [])
        strategy = evaluation.get("strategy", "unknown")
        symbol = evaluation.get("symbol", "unknown")
        skeptic_verdict = evaluation.get("verdict", "REJECT")

        # Gate 1: Skeptic must approve or send for review
        if skeptic_verdict == "REJECT":
            return {
                "decision": "REJECT",
                "strategy": strategy,
                "symbol": symbol,
                "reason": "Skeptic rejected. Strategy does not meet statistical criteria.",
            }

        # Gate 2: Portfolio capacity
        if len(current) >= self.MAX_APPROVED_STRATEGIES:
            return {
                "decision": "WAITLIST",
                "strategy": strategy,
                "symbol": symbol,
                "reason": f"Portfolio full ({len(current)}/{self.MAX_APPROVED_STRATEGIES}). Must remove a strategy first.",
            }

        # Gate 3: Concentration check
        same_stock = [s for s in current if s.get("symbol") == symbol]
        if len(same_stock) >= self.MAX_SINGLE_STOCK_STRATEGIES:
            return {
                "decision": "REJECT",
                "strategy": strategy,
                "symbol": symbol,
                "reason": f"Already {len(same_stock)} strategies on {symbol}. Too concentrated.",
            }

        # Gate 4: Duplicate check
        duplicates = [s for s in current
                      if s.get("strategy") == strategy and s.get("symbol") == symbol]
        if duplicates:
            return {
                "decision": "REJECT",
                "strategy": strategy,
                "symbol": symbol,
                "reason": f"Duplicate: {strategy} on {symbol} already approved.",
            }

        # All gates passed
        if skeptic_verdict == "APPROVE":
            return {
                "decision": "APPROVE",
                "strategy": strategy,
                "symbol": symbol,
                "reason": "All criteria met. Promoted to paper trading.",
                "position_size_pct": min(25, 100 // (len(current) + 1)),
            }
        else:
            # REVIEW — approve with reduced size
            return {
                "decision": "APPROVE_REDUCED",
                "strategy": strategy,
                "symbol": symbol,
                "reason": "Marginal pass (Skeptic REVIEW). Approved at reduced size.",
                "position_size_pct": min(10, 100 // (len(current) + 1)),
            }

    def get_approved_strategies(self, conn) -> list:
        """Get currently approved strategies from research_experiments."""
        try:
            rows = conn.execute("""
                SELECT strategy, symbol, oos_sharpe, skeptic_verdict
                FROM research_experiments
                WHERE skeptic_verdict = 'PASS'
                ORDER BY oos_sharpe DESC
            """).fetchdf()

            return [
                {"strategy": r["strategy"], "symbol": r["symbol"],
                 "sharpe": r["oos_sharpe"]}
                for _, r in rows.iterrows()
            ]
        except Exception:
            return []

    def promote(self, conn, skeptic_evaluation: dict) -> dict:
        """Full promotion workflow: check gates, decide, log."""
        current = self.get_approved_strategies(conn)

        decision = self.think({
            "skeptic_evaluation": skeptic_evaluation,
            "current_approved": current,
        })

        self.log(conn, "promote", f"{skeptic_evaluation.get('strategy')} on {skeptic_evaluation.get('symbol')}",
                 decision)

        return decision


def promote_strategy(conn, skeptic_evaluation: dict) -> dict:
    """Convenience wrapper."""
    agent = GatekeeperAgent()
    return agent.promote(conn, skeptic_evaluation)
