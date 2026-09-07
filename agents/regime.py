"""
Regime Classifier Agent: determines the current market environment.
Pure code — no LLM. Classifies from VIX and SPY features.

Regimes:
  HIGH_VOL:  VIX > 30 (panic)
  RISK_OFF:  VIX > 25 or SPY below MA50
  RISK_ON:   VIX < 18 and SPY above MA50
  LOW_VOL:   VIX < 15
  NEUTRAL:   everything else
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base import BaseAgent


class RegimeAgent(BaseAgent):
    def __init__(self):
        super().__init__("regime", "Classify the current market regime from VIX and SPY data.")

    def think(self, context: dict) -> dict:
        """
        context: dict with keys 'vix', 'vix_change_5d', 'spy_above_ma50' (bool)
        Returns: dict with 'regime', 'description', 'confidence'
        """
        vix = context.get("vix")
        vix_change = context.get("vix_change_5d", 0)
        spy_above_ma50 = context.get("spy_above_ma50", True)

        if vix is None:
            return {"regime": "UNKNOWN", "description": "No VIX data available", "confidence": 0}

        if vix > 30:
            regime = "HIGH_VOL"
            desc = f"Panic: VIX={vix:.1f}. Market in fear mode."
        elif vix > 25 or not spy_above_ma50:
            regime = "RISK_OFF"
            desc = f"Cautious: VIX={vix:.1f}, SPY {'below' if not spy_above_ma50 else 'above'} MA50."
        elif vix < 15:
            regime = "LOW_VOL"
            desc = f"Calm: VIX={vix:.1f}. Low volatility, complacent market."
        elif vix < 18 and spy_above_ma50:
            regime = "RISK_ON"
            desc = f"Bullish: VIX={vix:.1f}, SPY above MA50. Risk appetite high."
        else:
            regime = "NEUTRAL"
            desc = f"Neutral: VIX={vix:.1f}. No strong directional signal."

        # Add VIX trend
        if vix_change and abs(vix_change) > 0.15:
            direction = "rising" if vix_change > 0 else "falling"
            desc += f" VIX {direction} ({vix_change:+.0%} over 5d)."

        return {
            "regime": regime,
            "description": desc,
            "vix": vix,
            "spy_above_ma50": spy_above_ma50,
            "confidence": 0.8 if regime != "NEUTRAL" else 0.5,
        }


def get_current_regime(conn) -> dict:
    """Helper: get regime from latest DuckDB data."""
    agent = RegimeAgent()

    # Get latest VIX
    vix_row = conn.execute("""
        SELECT value, observation_date FROM macro_releases
        WHERE series_id = 'VIXCLS' ORDER BY observation_date DESC LIMIT 1
    """).fetchone()

    # Get VIX 5d ago
    vix_5d = conn.execute("""
        SELECT value FROM macro_releases
        WHERE series_id = 'VIXCLS' ORDER BY observation_date DESC LIMIT 1 OFFSET 5
    """).fetchone()

    # Check SPY vs MA50
    spy_ma = conn.execute("""
        SELECT distance_from_ma50 FROM daily_features
        WHERE symbol = 'TSLA' ORDER BY date DESC LIMIT 1
    """).fetchone()
    # Use any stock's SPY relative — or check SPY directly
    spy_price = conn.execute("""
        SELECT close FROM daily_bars
        WHERE symbol = 'SPY' ORDER BY timestamp DESC LIMIT 1
    """).fetchone()
    spy_ma50 = conn.execute("""
        SELECT AVG(close) FROM (
            SELECT close FROM daily_bars
            WHERE symbol = 'SPY' ORDER BY timestamp DESC LIMIT 50
        )
    """).fetchone()

    vix = vix_row[0] if vix_row else None
    vix_change = (vix / vix_5d[0] - 1) if (vix and vix_5d and vix_5d[0]) else 0
    spy_above = (spy_price[0] > spy_ma50[0]) if (spy_price and spy_ma50) else True

    context = {"vix": vix, "vix_change_5d": vix_change, "spy_above_ma50": spy_above}
    return agent.think(context)
