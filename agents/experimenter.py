"""
Experimenter Agent: takes a hypothesis, runs it through the backtest + Skeptic pipeline,
and records the result in research_experiments.

This agent doesn't invent strategies — it formally tests them. The Scout proposes
what to investigate, the Experimenter executes the test.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime
import duckdb
import pandas as pd
import config
from agents.base import BaseAgent
from scripts.backtester import get_prices, run_backtest
from scripts.storage import init_db


class ExperimenterAgent(BaseAgent):
    def __init__(self):
        super().__init__("experimenter", "Run formal backtests on hypotheses and record results.")

    def think(self, context: dict) -> dict:
        """
        context: {
            'strategy_fn': callable(conn, symbol) -> pd.Series,
            'strategy_name': str,
            'symbol': str,
            'cost_per_trade': float (optional),
            'split_date': str (optional),
        }
        """
        return {"response": "Use run_experiment() for formal testing."}

    def run_experiment(self, conn, strategy_fn, strategy_name: str, symbol: str,
                       cost_per_trade: float = 0.0005, split_date: str = "2023-01-01") -> dict:
        """
        Run a complete experiment: generate signal -> backtest -> Skeptic -> record.

        strategy_fn: callable(conn, symbol) -> pd.Series of {-1, 0, 1}
        Returns: backtest result dict with verdict
        """
        # Generate signal
        signal = strategy_fn(conn, symbol)
        if signal.empty or signal.abs().sum() == 0:
            result = {
                "strategy": strategy_name,
                "symbol": symbol,
                "error": "No signal generated",
                "verdict": "FAIL",
            }
            self._record_experiment(conn, strategy_name, symbol, result)
            return result

        # Get prices and run backtest
        prices = get_prices(conn, symbol)
        if prices.empty:
            result = {
                "strategy": strategy_name,
                "symbol": symbol,
                "error": "No price data",
                "verdict": "FAIL",
            }
            self._record_experiment(conn, strategy_name, symbol, result)
            return result

        bt = run_backtest(signal, prices, f"{strategy_name}_{symbol}",
                          cost_per_trade=cost_per_trade, split_date=split_date)

        # Extract key results
        oos = bt.get("out_of_sample", {})
        skeptic = bt.get("skeptic_report", {})

        result = {
            "strategy": strategy_name,
            "symbol": symbol,
            "oos_sharpe": oos.get("sharpe_ratio", 0),
            "oos_return": oos.get("annualized_return", 0),
            "oos_drawdown": oos.get("max_drawdown", 0),
            "oos_trades": oos.get("n_trades", 0),
            "skeptic_verdict": skeptic.get("verdict", "FAIL"),
            "tests_passed": skeptic.get("tests_passed", 0),
            "tests_total": skeptic.get("tests_total", 5),
            "beats_benchmark": bt.get("beats_benchmark", False),
            "overfit_warning": bt.get("overfit_warning", False),
        }

        self._record_experiment(conn, strategy_name, symbol, result)
        self.log(conn, "experiment", f"{strategy_name} on {symbol}", result,
                 regime=None)

        return result

    def _record_experiment(self, conn, strategy_name: str, symbol: str, result: dict):
        """Record experiment in research_experiments table."""
        try:
            conn.execute("""
                INSERT INTO research_experiments (strategy, symbol, parameters, 
                    oos_annualized_return, oos_sharpe, oos_max_drawdown,
                    skeptic_verdict, skeptic_tests_passed, skeptic_tests_total, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                strategy_name,
                symbol,
                json.dumps({"cost": 0.0005, "split": "2023-01-01"}),
                result.get("oos_return", 0),
                result.get("oos_sharpe", 0),
                result.get("oos_drawdown", 0),
                result.get("skeptic_verdict", "FAIL"),
                result.get("tests_passed", 0),
                result.get("tests_total", 5),
                result.get("error", ""),
            ])
        except Exception as e:
            pass  # Don't crash on logging failure


def run_experiment(conn, strategy_fn, strategy_name: str, symbol: str, **kwargs) -> dict:
    """Convenience wrapper."""
    agent = ExperimenterAgent()
    return agent.run_experiment(conn, strategy_fn, strategy_name, symbol, **kwargs)
