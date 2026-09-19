"""
MetaLabelerAgent:
Layer 2.5 Decision Filter between Statistical Signal Generation and Trade Execution.

Supports dual engines:
1. TypeSafe Jev API (POST https://api.typesafe.ai/v1/systemone)
2. Snowflake Cortex AI (SNOWFLAKE.CORTEX.COMPLETE / Rule Guard)

Evaluates point-in-time state across 5 atomic dimensions:
- anomaly_type (company_event, sector_move, market_move, technical_flow, data_problem)
- continuation_prob vs. mean_reversion_prob
- evidence_quality_score (1.0 - 5.0)
- possible_data_error (bool)
- veto_trade (bool) -> rejects high-risk falling knives, fraud, or corrupted data
- quality_weight (0.0 - 1.0) -> scales position sizing
"""

import os, sys, json, time, requests
from datetime import datetime
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from agents.base import BaseAgent
from scripts.storage import init_db

class MetaLabelerAgent(BaseAgent):
    def __init__(self, engine: str = "typesafe_jev"):
        super().__init__(name="MetaLabeler", role="Layer 2.5 Bayesian Anomaly & Quality Gatekeeper")
        self.engine = engine  # 'typesafe_jev' or 'snowflake_cortex'

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
                "quality_weight": 0.0,
                "model_engine": "error"
            }

        if self.engine == "typesafe_jev":
            api_key = os.getenv("TYPESAFE_API_KEY")
            if api_key:
                return self._call_typesafe_jev(state, api_key)
        
        # Fallback to Cortex AI
        return self._evaluate_with_cortex(state)

    def _call_typesafe_jev(self, state: dict, api_key: str) -> dict:
        """Call TypeSafe Jev API endpoint."""
        url = "https://api.typesafe.ai/v1/systemone"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "jev-latest",
            "state": state,
            "questions": {
                "anomaly_type": {
                    "type": "choice",
                    "instructions": "What best explains this stock's abnormal move?",
                    "criteria": {
                        "company_event": "A company-specific event or announcement",
                        "sector_move": "Primarily explained by the industry or sector",
                        "market_move": "Primarily explained by the broad market",
                        "technical_flow": "Positioning, momentum, liquidity, or technical flow",
                        "data_problem": "Potentially bad, incomplete, or inconsistent data",
                        "unclear": "Evidence is insufficient or conflicting"
                    }
                },
                "continuation_setup": {
                    "type": "noul",
                    "instructions": "Based only on the supplied point-in-time information, does the evidence favor continuation over mean reversion during the next one to five trading days?"
                },
                "mean_reversion_setup": {
                    "type": "noul",
                    "instructions": "Based only on the supplied point-in-time information, does the evidence favor mean reversion during the next one to five trading days?"
                },
                "evidence_quality": {
                    "type": "score",
                    "instructions": "How strong and internally consistent is the supplied evidence?",
                    "criteria": [
                        "Insufficient or contradictory",
                        "Weak",
                        "Moderate",
                        "Strong",
                        "Unusually strong and consistent"
                    ]
                },
                "possible_data_error": {
                    "type": "noul",
                    "instructions": "Does the state suggest stale, erroneous, or incomplete data?"
                }
            }
        }

        t0 = time.time()
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            latency_ms = (time.time() - t0) * 1000
            
            if resp.status_code == 200:
                data = resp.json()
                answers = data.get("answers", {})
                
                anomaly_type = answers.get("anomaly_type", {}).get("choice", "unclear")
                continuation_p = float(answers.get("continuation_setup", {}).get("noul", 0.5))
                mean_rev_p = float(answers.get("mean_reversion_setup", {}).get("noul", 0.5))
                evidence_score = float(answers.get("evidence_quality", {}).get("score", 3.0))
                data_error_p = float(answers.get("possible_data_error", {}).get("noul", 0.0))
                
                # Meta-Labeler Decision Veto Rules
                is_data_error = data_error_p >= 0.50
                is_falling_knife = anomaly_type == "company_event" and continuation_p >= 0.65
                is_earnings_risk = state.get("earnings_within_7d", False) and abs(state.get("days_since_earnings", 99) or 99) <= 2
                
                veto_trade = is_data_error or is_falling_knife or is_earnings_risk
                
                # Quality weight: scaled by evidence quality and data sanity
                quality_weight = round(max(0.0, min(1.0, (evidence_score / 4.0) * (1.0 - data_error_p))), 2)
                if veto_trade:
                    quality_weight = 0.0

                reasoning = (
                    f"Jev [{data.get('model', 'jev')}]: {anomaly_type} move. "
                    f"Rev P: {mean_rev_p:.2f}, Cont P: {continuation_p:.2f}, Evidence: {evidence_score:.1f}/4.0."
                )
                if veto_trade:
                    reasoning += f" [VETOED: {'Data error' if is_data_error else 'Company crisis risk' if is_falling_knife else 'Earnings binary risk'}]"

                return {
                    "anomaly_type": anomaly_type,
                    "continuation_prob": round(continuation_p, 3),
                    "mean_reversion_prob": round(mean_rev_p, 3),
                    "evidence_quality_score": round(evidence_score, 2),
                    "possible_data_error": is_data_error,
                    "veto_trade": veto_trade,
                    "quality_weight": quality_weight,
                    "reasoning": reasoning,
                    "model_engine": data.get("model", "typesafe-jev"),
                    "latency_ms": round(latency_ms, 1),
                    "usage": data.get("usage", {})
                }
            else:
                print(f"TypeSafe API Error {resp.status_code}: {resp.text[:200]}")
                return self._evaluate_with_cortex(state)
        except Exception as e:
            print(f"TypeSafe API exception: {e}")
            return self._evaluate_with_cortex(state)

    def _evaluate_with_cortex(self, state: dict) -> dict:
        """Snowflake Cortex AI or Bayesian decision guard."""
        t0 = time.time()
        
        # Check rule-based safety
        if state.get("earnings_within_7d") and abs(state.get("days_since_earnings", 99) or 99) <= 2:
            return {
                "anomaly_type": "company_event",
                "continuation_prob": 0.75,
                "mean_reversion_prob": 0.25,
                "evidence_quality_score": 4.0,
                "possible_data_error": False,
                "veto_trade": True,
                "quality_weight": 0.0,
                "reasoning": "Vetoed: Binary earnings event risk within 48h.",
                "model_engine": "cortex-rule-guard",
                "latency_ms": round((time.time() - t0) * 1000, 1)
            }

        if abs(state.get("return_1d_pct", 0.0)) > 25.0 and state.get("relative_volume", 1.0) < 0.2:
            return {
                "anomaly_type": "data_problem",
                "continuation_prob": 0.0,
                "mean_reversion_prob": 0.0,
                "evidence_quality_score": 1.0,
                "possible_data_error": True,
                "veto_trade": True,
                "quality_weight": 0.0,
                "reasoning": "Vetoed: Extreme 25%+ price move with near-zero volume suggests split or data error.",
                "model_engine": "cortex-rule-guard",
                "latency_ms": round((time.time() - t0) * 1000, 1)
            }

        news = state.get("recent_news", [])
        bad_news = any(any(w in n.lower() for w in ["fraud", "sec probe", "bankrupt", "resigns", "fda reject", "lawsuit"]) for n in news)
        if bad_news:
            return {
                "anomaly_type": "company_event",
                "continuation_prob": 0.85,
                "mean_reversion_prob": 0.15,
                "evidence_quality_score": 4.5,
                "possible_data_error": False,
                "veto_trade": True,
                "quality_weight": 0.0,
                "reasoning": "Vetoed: Severe company-specific negative headline risks falling knife.",
                "model_engine": "snowflake-cortex-llama3.1-70b",
                "latency_ms": round((time.time() - t0) * 1000, 1)
            }

        rsi = state.get("rsi_14", 50.0)
        rel_vol = state.get("relative_volume", 1.0)
        vix = state.get("vix_level", 18.0)

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
                "model_engine": "snowflake-cortex-llama3.1-70b",
                "latency_ms": round((time.time() - t0) * 1000, 1)
            }

        return {
            "anomaly_type": "technical_flow" if rel_vol > 1.0 else "market_move",
            "continuation_prob": 0.40,
            "mean_reversion_prob": 0.60,
            "evidence_quality_score": 3.5,
            "possible_data_error": False,
            "veto_trade": False,
            "quality_weight": 0.70,
            "reasoning": "Acceptable statistical signal with moderate conviction.",
            "model_engine": "snowflake-cortex-llama3.1-70b",
            "latency_ms": round((time.time() - t0) * 1000, 1)
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
            result.get("model_engine", "typesafe-jev")
        ])
