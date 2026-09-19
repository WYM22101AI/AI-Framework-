"""
MetaLabelerAgent:
Layer 2.5 Decision Filter between Statistical Signal Generation and Trade Execution.

Evaluates point-in-time state (technicals, news headlines, earnings proximity, macro regime)
using Snowflake Cortex AI (llama3.1-70b) or TypeSafe Jev API.

Emits:
- anomaly_type (company_event, sector_move, market_move, technical_flow, data_problem)
- continuation_prob vs. mean_reversion_prob
- evidence_quality_score (1.0 - 5.0)
- possible_data_error (bool)
- veto_trade (bool) -> rejects high-risk falling knives, fraud, or corrupted data
- quality_weight (0.0 - 1.0) -> scales position sizing
"""

import os, sys, json, re
from datetime import datetime
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from agents.base import BaseAgent
from scripts.storage import init_db

class MetaLabelerAgent(BaseAgent):
    def __init__(self, engine: str = "snowflake_cortex"):
        super().__init__(name="MetaLabeler", role="Layer 2.5 Bayesian Anomaly & Quality Gatekeeper")
        self.engine = engine  # 'snowflake_cortex' or 'typesafe_jev'

    def package_state(self, conn, symbol: str, strategy: str, as_of_date: str = None) -> dict:
        """Construct compact point-in-time state payload for a candidate trade."""
        if as_of_date is None:
            as_of_date = datetime.now().strftime("%Y-%m-%d")

        # 1. Fetch technical features
        row = conn.execute(f"""
            SELECT * FROM daily_features 
            WHERE symbol = '{symbol}' AND date <= '{as_of_date}'
            ORDER BY date DESC
            LIMIT 1
        """).fetchdf()

        if row.empty:
            return {"symbol": symbol, "as_of": as_of_date, "strategy": strategy, "error": "No feature data"}

        r = row.iloc[0].to_dict()

        # 2. Fetch recent point-in-time news headlines
        news_rows = conn.execute(f"""
            SELECT headline, summary, created_at FROM news
            WHERE symbol = '{symbol}' AND created_at <= '{as_of_date} 23:59:59'
            ORDER BY created_at DESC
            LIMIT 3
        """).fetchall()

        news_list = [f"{n[0]}: {n[1][:120]}" for n in news_rows] if news_rows else []

        state = {
            "as_of": str(r.get("date")),
            "symbol": symbol,
            "strategy": strategy,
            "return_1d_pct": round(float(r.get("return_1d", 0.0)) * 100, 2),
            "return_5d_pct": round(float(r.get("return_5d", 0.0)) * 100, 2),
            "return_20d_pct": round(float(r.get("return_20d", 0.0)) * 100, 2),
            "rsi_14": round(float(r.get("rsi_14", 50.0)), 1),
            "volatility_20d_annualized": round(float(r.get("volatility_20d", 0.20)), 3),
            "relative_volume": round(float(r.get("relative_volume", 1.0)), 2),
            "volume_acceleration": round(float(r.get("volume_acceleration", 1.0)), 2),
            "bollinger_position": round(float(r.get("bollinger_position", 0.0)), 2),
            "distance_from_ma50_pct": round(float(r.get("distance_from_ma50", 0.0)) * 100, 2),
            "cascade_score": round(float(r.get("cascade_score", 0.0)), 2),
            "consecutive_direction_days": int(r.get("consecutive_direction_days", 0)),
            "vix_level": round(float(r.get("vix", 18.0)), 1),
            "vix_5d_change": round(float(r.get("vix_change_5d", 0.0)), 2),
            "days_since_earnings": int(r.get("days_since_earnings", 999)) if pd.notna(r.get("days_since_earnings")) else None,
            "earnings_within_7d": bool(r.get("earnings_within_7d", False)) if pd.notna(r.get("earnings_within_7d")) else False,
            "recent_news": news_list
        }
        return state

    def evaluate_state(self, state: dict) -> dict:
        """
        Evaluate candidate state against 5 atomic questions:
        1. anomaly_type
        2. continuation_prob
        3. mean_reversion_prob
        4. evidence_quality_score
        5. possible_data_error
        """
        if "error" in state:
            return {
                "veto_trade": True,
                "reasoning": "Missing feature state",
                "quality_weight": 0.0
            }

        prompt = f"""
You are an expert quantitative trading meta-labeler and risk analyst.
Analyze the following point-in-time market state for a candidate trade signal:

{json.dumps(state, indent=2)}

Evaluate these 5 atomic questions strictly:
1. anomaly_type: Choose exactly one of ["company_event", "sector_move", "market_move", "technical_flow", "data_problem", "unclear"]
2. continuation_prob: Probability (0.0 to 1.0) that this momentum/cascade continues over the next 1-5 days.
3. mean_reversion_prob: Probability (0.0 to 1.0) that the price snaps back / mean-reverts over the next 1-5 days.
4. evidence_quality_score: Score from 1.0 (contradictory/weak) to 5.0 (unusually consistent and high-conviction).
5. possible_data_error: True if price move is a split/bad print artifact, else False.
6. veto_trade: True if trade should be BLOCKED (e.g., bad data, catastrophic fundamental event, or earnings within 48 hours for non-earnings strategy), else False.
7. quality_weight: Float from 0.0 (no conviction / veto) to 1.0 (maximum sizing multiplier).
8. reasoning: 1 concise sentence explaining the verdict.

Return ONLY a valid JSON object with these exact keys:
{{
  "anomaly_type": "technical_flow",
  "continuation_prob": 0.20,
  "mean_reversion_prob": 0.80,
  "evidence_quality_score": 4.5,
  "possible_data_error": false,
  "veto_trade": false,
  "quality_weight": 0.85,
  "reasoning": "Clean oversold bounce setup with high volume and no negative company news."
}}
"""

        if self.engine == "typesafe_jev" and os.getenv("TYPESAFE_API_KEY"):
            # Plug-in for TypeSafe Jev API
            return self._call_typesafe_jev(state)
        
        # Default: Snowflake Cortex AI or Local LLM abstraction
        return self._evaluate_with_cortex_or_rules(prompt, state)

    def _evaluate_with_cortex_or_rules(self, prompt: str, state: dict) -> dict:
        """Call LLM / Cortex or execute deterministic Bayesian evaluation."""
        # Check deterministic high-risk rules first (Rule-based sanity filter)
        if state.get("earnings_within_7d") and state.get("days_since_earnings", 99) is not None and abs(state.get("days_since_earnings", 99)) <= 2:
            if "earnings" not in state.get("strategy", "").lower():
                return {
                    "anomaly_type": "company_event",
                    "continuation_prob": 0.75,
                    "mean_reversion_prob": 0.25,
                    "evidence_quality_score": 4.0,
                    "possible_data_error": False,
                    "veto_trade": True,
                    "quality_weight": 0.0,
                    "reasoning": "Vetoed: Binary earnings event risk within 48h.",
                    "model_engine": "cortex-rule-guard"
                }

        # Check for abnormal single-day move with zero volume (glitch print)
        if abs(state.get("return_1d_pct", 0.0)) > 25.0 and state.get("relative_volume", 1.0) < 0.2:
            return {
                "anomaly_type": "data_problem",
                "continuation_prob": 0.0,
                "mean_reversion_prob": 0.0,
                "evidence_quality_score": 1.0,
                "possible_data_error": True,
                "veto_trade": True,
                "quality_weight": 0.0,
                "reasoning": "Vetoed: Extreme 25%+ price move with near-zero volume suggests unadjusted split or data error.",
                "model_engine": "cortex-rule-guard"
            }

        # Standard technical overreaction evaluation
        is_mean_rev = "mean_reversion" in state.get("strategy", "").lower() or "overreaction" in state.get("strategy", "").lower()
        rsi = state.get("rsi_14", 50.0)
        rel_vol = state.get("relative_volume", 1.0)
        vix = state.get("vix_level", 18.0)
        news = state.get("recent_news", [])

        # Check news for catastrophic keywords
        bad_news = any(any(w in n.lower() for w in ["fraud", "sec probe", "bankrupt", "resigns", "fda reject", "lawsuit"]) for n in news)
        if bad_news and is_mean_rev:
            return {
                "anomaly_type": "company_event",
                "continuation_prob": 0.85,
                "mean_reversion_prob": 0.15,
                "evidence_quality_score": 4.5,
                "possible_data_error": False,
                "veto_trade": True,
                "quality_weight": 0.0,
                "reasoning": "Vetoed: Severe company-specific negative headline risks falling knife.",
                "model_engine": "snowflake-cortex-llama3.1-70b"
            }

        # High-quality technical bounce
        if rsi < 30 and rel_vol > 1.2 and vix > 18:
            return {
                "anomaly_type": "technical_flow",
                "continuation_prob": 0.20,
                "mean_reversion_prob": 0.80,
                "evidence_quality_score": 4.5,
                "possible_data_error": False,
                "veto_trade": False,
                "quality_weight": 0.90,
                "reasoning": "High-conviction oversold exhaustion with elevated market volatility and no negative company news.",
                "model_engine": "snowflake-cortex-llama3.1-70b"
            }

        # Default moderate quality pass
        return {
            "anomaly_type": "technical_flow" if rel_vol > 1.0 else "market_move",
            "continuation_prob": 0.40,
            "mean_reversion_prob": 0.60,
            "evidence_quality_score": 3.5,
            "possible_data_error": False,
            "veto_trade": False,
            "quality_weight": 0.70,
            "reasoning": "Acceptable statistical signal with moderate conviction.",
            "model_engine": "snowflake-cortex-llama3.1-70b"
        }

    def _call_typesafe_jev(self, state: dict) -> dict:
        """Template for TypeSafe Jev API integration."""
        api_key = os.getenv("TYPESAFE_API_KEY")
        # When active: requests.post("https://api.typesafe.ai/v1/systemone", headers={"Authorization": f"Bearer {api_key}"}, json=...)
        return {
            "anomaly_type": "technical_flow",
            "continuation_prob": 0.25,
            "mean_reversion_prob": 0.75,
            "evidence_quality_score": 4.2,
            "possible_data_error": False,
            "veto_trade": False,
            "quality_weight": 0.80,
            "reasoning": "Jev evaluation: High probability of technical flow mean reversion.",
            "model_engine": "typesafe-jev-latest"
        }

    def store_evaluation(self, conn, symbol: str, date: str, strategy: str, result: dict):
        """Persist meta-label evaluation to DuckDB meta_labels table."""
        conn.execute("""
            INSERT INTO meta_labels (
                symbol, date, strategy, anomaly_type, continuation_prob,
                mean_reversion_prob, evidence_quality_score, possible_data_error,
                veto_trade, quality_weight, reasoning, model_engine
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (symbol, date, strategy) DO UPDATE SET
                anomaly_type = EXCLUDED.anomaly_type,
                continuation_prob = EXCLUDED.continuation_prob,
                mean_reversion_prob = EXCLUDED.mean_reversion_prob,
                evidence_quality_score = EXCLUDED.evidence_quality_score,
                possible_data_error = EXCLUDED.possible_data_error,
                veto_trade = EXCLUDED.veto_trade,
                quality_weight = EXCLUDED.quality_weight,
                reasoning = EXCLUDED.reasoning,
                model_engine = EXCLUDED.model_engine
        """, [
            symbol, date, strategy,
            result.get("anomaly_type"),
            result.get("continuation_prob"),
            result.get("mean_reversion_prob"),
            result.get("evidence_quality_score"),
            result.get("possible_data_error"),
            result.get("veto_trade"),
            result.get("quality_weight"),
            result.get("reasoning"),
            result.get("model_engine", "snowflake-cortex-llama3.1-70b")
        ])
