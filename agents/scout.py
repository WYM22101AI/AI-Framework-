"""
Scout Agent: daily anomaly scanner.
Scans features for unusual conditions across all stocks.
Does NOT recommend trades — just flags things worth investigating.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from agents.base import BaseAgent


class ScoutAgent(BaseAgent):
    def __init__(self):
        super().__init__("scout", "Find unusual market conditions that may warrant investigation.")

    def think(self, features: pd.DataFrame) -> dict:
        """
        features: latest daily_features for all stocks (one row per stock)
        Returns: dict with 'anomalies' (list) and 'summary'
        """
        anomalies = []

        for _, row in features.iterrows():
            symbol = row["symbol"]
            flags = []

            # Unusual volume
            if pd.notna(row.get("relative_volume")) and row["relative_volume"] > 2.5:
                flags.append(f"volume {row['relative_volume']:.1f}x normal")

            # RSI extremes
            if pd.notna(row.get("rsi_14")):
                if row["rsi_14"] < 25:
                    flags.append(f"deeply oversold (RSI {row['rsi_14']:.0f})")
                elif row["rsi_14"] > 75:
                    flags.append(f"deeply overbought (RSI {row['rsi_14']:.0f})")

            # Large daily move
            if pd.notna(row.get("return_1d")):
                if abs(row["return_1d"]) > 0.03:
                    direction = "up" if row["return_1d"] > 0 else "down"
                    flags.append(f"big move {direction} ({row['return_1d']*100:+.1f}%)")

            # Bollinger extreme
            if pd.notna(row.get("bollinger_position")):
                if row["bollinger_position"] < -1.5:
                    flags.append(f"far below Bollinger ({row['bollinger_position']:.1f})")
                elif row["bollinger_position"] > 1.5:
                    flags.append(f"far above Bollinger ({row['bollinger_position']:.1f})")

            # Earnings soon
            earnings_flag = row.get("earnings_within_7d")
            if pd.notna(earnings_flag) and earnings_flag:
                flags.append("earnings within 7 days")

            # Extreme relative strength
            if pd.notna(row.get("relative_strength_vs_spy")):
                if abs(row["relative_strength_vs_spy"]) > 0.15:
                    direction = "outperforming" if row["relative_strength_vs_spy"] > 0 else "underperforming"
                    flags.append(f"strongly {direction} SPY ({row['relative_strength_vs_spy']:+.1%})")

            if flags:
                anomalies.append({
                    "symbol": symbol,
                    "flags": flags,
                    "flag_count": len(flags),
                })

        # Sort by number of flags (most unusual first)
        anomalies.sort(key=lambda x: x["flag_count"], reverse=True)

        if anomalies:
            summary = f"Found {len(anomalies)} stocks with unusual conditions. Top: {anomalies[0]['symbol']} ({', '.join(anomalies[0]['flags'])})"
        else:
            summary = "No unusual conditions detected. Market appears normal."

        return {
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
            "summary": summary,
        }


def scan_anomalies(conn) -> dict:
    """Helper: run scout on latest features from DuckDB."""
    agent = ScoutAgent()

    # Get latest date's features for all stocks
    latest = conn.execute("""
        SELECT * FROM daily_features
        WHERE date = (SELECT MAX(date) FROM daily_features)
        ORDER BY symbol
    """).fetchdf()

    if latest.empty:
        return {"anomalies": [], "anomaly_count": 0, "summary": "No feature data available."}

    return agent.think(latest)
