"""
Skeptic Agent: the kill switch. Evaluates experiment results and decides
whether a strategy should advance or die.

The Skeptic never runs statistics directly — it interprets the output of
stats_engine (called by the Experimenter) and applies judgment.

Kill criteria:
1. Skeptic verdict must be PASS (4/5 tests) or WEAK (3/5)
2. OOS Sharpe > 0.5
3. Max drawdown < -30%
4. Must beat SPY buy-and-hold
5. No overfitting warning
6. Minimum 30 OOS trades (enough data to trust)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base import BaseAgent


class SkepticAgent(BaseAgent):
    def __init__(self):
        super().__init__("skeptic", "Evaluate experiment results. Kill bad strategies, advance good ones.")

    # Configurable thresholds
    MIN_SHARPE = 0.5
    MAX_DRAWDOWN = -0.30
    MIN_TRADES = 30
    MIN_TESTS_PASSED = 3  # 3/5 = WEAK, 4/5 = PASS

    def think(self, experiment_result: dict) -> dict:
        """
        Evaluate an experiment result from the Experimenter.
        Returns: verdict (APPROVE / REVIEW / REJECT), reasons, recommendation.
        """
        reasons = []
        flags = []

        strategy = experiment_result.get("strategy", "unknown")
        symbol = experiment_result.get("symbol", "unknown")

        # Check for errors
        if experiment_result.get("error"):
            return {
                "verdict": "REJECT",
                "strategy": strategy,
                "symbol": symbol,
                "reasons": [f"Error: {experiment_result['error']}"],
                "recommendation": "Fix the error and re-run.",
            }

        sharpe = experiment_result.get("oos_sharpe", 0)
        drawdown = experiment_result.get("oos_drawdown", 0)
        trades = experiment_result.get("oos_trades", 0)
        tests_passed = experiment_result.get("tests_passed", 0)
        verdict = experiment_result.get("skeptic_verdict", "FAIL")
        beats_bench = experiment_result.get("beats_benchmark", False)
        overfit = experiment_result.get("overfit_warning", False)

        # Apply kill criteria
        if verdict == "PASS":
            reasons.append(f"Skeptic battery: PASS ({tests_passed}/5)")
        elif verdict == "WEAK":
            flags.append(f"Skeptic battery: WEAK ({tests_passed}/5) — marginal")
        else:
            reasons.append(f"Skeptic battery: FAIL ({tests_passed}/5)")

        if sharpe >= self.MIN_SHARPE:
            reasons.append(f"OOS Sharpe {sharpe:.2f} >= {self.MIN_SHARPE}")
        else:
            reasons.append(f"OOS Sharpe {sharpe:.2f} < {self.MIN_SHARPE} — insufficient edge")

        if drawdown >= self.MAX_DRAWDOWN:
            reasons.append(f"Max drawdown {drawdown:.1%} acceptable")
        else:
            reasons.append(f"Max drawdown {drawdown:.1%} too deep (limit {self.MAX_DRAWDOWN:.0%})")

        if trades >= self.MIN_TRADES:
            reasons.append(f"{trades} OOS trades (sufficient sample)")
        else:
            flags.append(f"Only {trades} OOS trades — not enough to trust")

        if beats_bench:
            reasons.append("Beats SPY buy-and-hold")
        else:
            reasons.append("Does NOT beat SPY buy-and-hold")

        if overfit:
            flags.append("Overfitting warning: IS Sharpe >> OOS Sharpe")

        # Final decision
        passes = [
            tests_passed >= self.MIN_TESTS_PASSED,
            sharpe >= self.MIN_SHARPE,
            drawdown >= self.MAX_DRAWDOWN,
            beats_bench,
            not overfit,
        ]
        pass_count = sum(passes)

        if pass_count >= 5:
            final = "APPROVE"
            rec = f"Promote {strategy} on {symbol} to paper trading."
        elif pass_count >= 4 and verdict != "FAIL":
            final = "REVIEW"
            rec = f"Close to passing. Review flags: {'; '.join(flags) if flags else 'minor concerns'}."
        else:
            final = "REJECT"
            rec = f"Kill {strategy} on {symbol}. {5 - pass_count} criteria failed."

        result = {
            "verdict": final,
            "strategy": strategy,
            "symbol": symbol,
            "pass_count": pass_count,
            "pass_total": 5,
            "reasons": reasons,
            "flags": flags,
            "recommendation": rec,
        }

        return result


def evaluate_experiment(conn, experiment_result: dict) -> dict:
    """Convenience wrapper: evaluate and log."""
    agent = SkepticAgent()
    evaluation = agent.think(experiment_result)
    agent.log(conn, "evaluate", f"{experiment_result.get('strategy')} on {experiment_result.get('symbol')}",
              evaluation)
    return evaluation
