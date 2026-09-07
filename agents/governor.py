"""
Governor Agent: manages the research agenda.
Uses LLM to review results, propose hypotheses, and decide next steps.

For now, uses a rule-based approach (no LLM required).
Can be upgraded to use Cortex AI_COMPLETE or OpenAI later.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime, timedelta
from agents.base import BaseAgent


class GovernorAgent(BaseAgent):
    def __init__(self):
        super().__init__("governor", "Review research results, propose new hypotheses, manage the research agenda.")

    def weekly_review(self, conn) -> dict:
        """
        Run a weekly review of the research system.
        Looks at: agent_log, research_experiments, trade_log, anomaly patterns.
        Returns: recommendations for next week.
        """
        findings = []
        recommendations = []

        # 1. Check experiment history
        try:
            experiments = conn.execute("""
                SELECT strategy, symbol, oos_annualized_return, oos_sharpe, skeptic_verdict
                FROM research_experiments
                ORDER BY created_at DESC
                LIMIT 20
            """).fetchdf()

            if not experiments.empty:
                passes = experiments[experiments["skeptic_verdict"] == "PASS"]
                fails = experiments[experiments["skeptic_verdict"] == "FAIL"]
                findings.append(f"Experiments: {len(passes)} passes, {len(fails)} fails out of {len(experiments)} recent tests.")

                # Check if any strategy category is consistently failing
                by_strategy = experiments.groupby("strategy")["skeptic_verdict"].apply(
                    lambda x: (x == "FAIL").mean()
                )
                dead_strategies = by_strategy[by_strategy == 1.0].index.tolist()
                if dead_strategies:
                    findings.append(f"Dead strategies (100% fail rate): {dead_strategies}")
                    recommendations.append(f"Stop testing: {dead_strategies}. Focus on variants of passing strategies.")
        except Exception:
            findings.append("No experiment data available yet.")

        # 2. Check recent agent anomalies
        try:
            recent_anomalies = conn.execute("""
                SELECT result FROM agent_log
                WHERE agent_name = 'scout'
                AND timestamp > CURRENT_TIMESTAMP - INTERVAL 7 DAY
                ORDER BY timestamp DESC
                LIMIT 7
            """).fetchdf()

            if not recent_anomalies.empty:
                total_anomalies = 0
                for _, row in recent_anomalies.iterrows():
                    try:
                        data = json.loads(row["result"])
                        total_anomalies += data.get("anomaly_count", 0)
                    except (json.JSONDecodeError, TypeError):
                        pass
                findings.append(f"Scout found {total_anomalies} anomalies across {len(recent_anomalies)} days this week.")
        except Exception:
            pass

        # 3. Check paper trading activity
        try:
            trades = conn.execute("""
                SELECT COUNT(*) as cnt FROM trade_log
                WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL 7 DAY
            """).fetchone()
            if trades:
                findings.append(f"Paper trading: {trades[0]} orders this week.")
                if trades[0] == 0:
                    recommendations.append("No trades this week. Consider: is the strategy too selective? Or is the market simply not in the right regime?")
        except Exception:
            pass

        # 4. Generate research hypotheses
        hypotheses = self._generate_hypotheses(findings)
        recommendations.extend(hypotheses)

        return {
            "review_date": datetime.now().strftime("%Y-%m-%d"),
            "findings": findings,
            "recommendations": recommendations,
            "status": "ACTIVE" if recommendations else "STABLE",
        }

    def _generate_hypotheses(self, findings: list) -> list:
        """Generate research hypotheses based on current state. Rule-based for now."""
        hypotheses = []

        # Always suggest these if not yet tested
        hypotheses.append("Hypothesis: Test VIX mean reversion on index ETFs (QQQ, IWM, DIA) — do indices show the same oversold bounce as individual stocks?")
        hypotheses.append("Hypothesis: Combine mean reversion signal with earnings proximity — does the strategy perform differently near earnings?")

        return hypotheses

    def think(self, context: str) -> dict:
        """Simple wrapper for ad-hoc questions."""
        return {"response": "Governor agent: use weekly_review() for structured review."}


def run_weekly_review(conn) -> dict:
    """Helper: run the governor's weekly review."""
    governor = GovernorAgent()
    result = governor.weekly_review(conn)
    governor.log(conn, "weekly_review", "Scheduled weekly review", result)
    return result
