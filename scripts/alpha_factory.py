"""
Alpha Factory v1: Multi-Family Statistical Alpha Generator
Computes 6 independent price and relative-value alpha signals across the S&P 500 universe:
1. Alpha 1: Medium-Term Momentum (12-1m Momentum, excluding recent month)
2. Alpha 2: Short-Term Reversal (5-Day Oversold Panic Rebound)
3. Alpha 3: Trend Acceleration (2nd Derivative / Velocity Change)
4. Alpha 4: Volatility Compression Squeeze Breakout
5. Alpha 5: Sector-Relative Residual Alpha (Stock Return minus Sector ETF Return)
6. Alpha 6: Intra-Sector Peer Mean Reversion (Stock vs Basket Peers)

Constructs the Alpha Independence Correlation Matrix to verify low correlation (|rho| < 0.35).
"""

import sys, os
from datetime import datetime
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import duckdb, config
from scripts.storage import init_db

# Sector ETF mappings for Sector-Relative Residual Alpha
SECTOR_ETF_MAP = {
    "AMZN": "XLY", "TSLA": "XLY", "HD": "XLY", "NKE": "XLY", "MCD": "XLY",
    "AAPL": "XLK", "MSFT": "XLK", "NVDA": "XLK", "AMD": "XLK", "CRM": "XLK", "QCOM": "XLK",
    "JPM": "XLF", "GS": "XLF", "MS": "XLF", "BAC": "XLF", "V": "XLF", "MA": "XLF", "BLK": "XLF", "BRO": "XLF",
    "XOM": "XLE", "CVX": "XLE", "COP": "XLE",
    "CAT": "XLI", "GE": "XLI", "BA": "XLI", "UNP": "XLI", "HON": "XLI",
    "JNJ": "XLV", "UNH": "XLV", "LLY": "XLV", "PFE": "XLV", "ABBV": "XLV", "MRK": "XLV",
    "COST": "XLP", "PG": "XLP", "KO": "XLP", "WMT": "XLP", "TGT": "XLP",
    "NEE": "XLU", "PLD": "XLRE", "LIN": "XLB", "GOOG": "XLC", "META": "XLC", "DIS": "XLC", "NFLX": "XLC"
}

# Industry peer groups for Intra-Sector Peer Mean Reversion
PEER_GROUPS = {
    "FINANCIAL_BANKS": ["JPM", "BAC", "MS", "GS"],
    "BIG_TECH": ["AAPL", "MSFT", "GOOG", "AMZN", "META"],
    "SEMICONDUCTORS": ["NVDA", "AMD", "QCOM", "INTC"],
    "CONSUMER_RETAIL": ["COST", "WMT", "TGT", "HD"],
    "HEALTHCARE_PHARMA": ["LLY", "UNH", "JNJ", "PFE", "ABBV"],
    "ENERGY_MAJORS": ["XOM", "CVX", "COP"],
    "INDUSTRIALS": ["CAT", "GE", "BA", "HON"]
}

class AlphaFactory:
    """Multi-Family Statistical Alpha Generator & Independence Auditor."""

    def __init__(self, db_path: str = config.DB_PATH):
        self.db_path = db_path

    # ----------------------------------------------------------------------------------
    # 1. ALPHA 1: MEDIUM-TERM MOMENTUM (12-1m MOMENTUM)
    # ----------------------------------------------------------------------------------
    def compute_alpha_12_1_momentum(self, close_series: pd.Series) -> pd.Series:
        """12-month return excluding the most recent month (252d to 21d)."""
        ret_12m = close_series.shift(21) / close_series.shift(252) - 1.0
        ma50 = close_series.rolling(50).mean()
        # Signal = 1 if momentum is positive and price > 50-day MA
        sig = ((ret_12m > 0.05) & (close_series > ma50)).astype(int)
        return sig.fillna(0)

    # ----------------------------------------------------------------------------------
    # 2. ALPHA 2: SHORT-TERM REVERSAL (5-DAY EXTREME PANIC)
    # ----------------------------------------------------------------------------------
    def compute_alpha_short_term_reversal(self, close_series: pd.Series) -> pd.Series:
        """Oversold panic drop: 5-day drop < -4.0% and distance to 20 SMA < -3.0%."""
        ret5 = close_series.pct_change(5)
        sma20 = close_series.rolling(20).mean()
        dist_sma20 = (close_series - sma20) / sma20
        sig = ((ret5 < -0.04) & (dist_sma20 < -0.03)).astype(int).rolling(2).max()
        return sig.fillna(0)

    # ----------------------------------------------------------------------------------
    # 3. ALPHA 3: TREND ACCELERATION (2ND DERIVATIVE / VELOCITY CHANGE)
    # ----------------------------------------------------------------------------------
    def compute_alpha_trend_acceleration(self, close_series: pd.Series) -> pd.Series:
        """Measures whether velocity of trend is speeding up: Return_20d - Return_60d."""
        ret20 = close_series.pct_change(20)
        ret60 = close_series.pct_change(60)
        accel = ret20 - (ret60 / 3.0) # Normalized acceleration
        sig = (accel > 0.03).astype(int).rolling(5).max()
        return sig.fillna(0)

    # ----------------------------------------------------------------------------------
    # 4. ALPHA 4: VOLATILITY COMPRESSION SQUEEZE BREAKOUT
    # ----------------------------------------------------------------------------------
    def compute_alpha_volatility_squeeze(self, close_series: pd.Series) -> pd.Series:
        """Bollinger Bandwidth Squeeze followed by price break above upper band."""
        sma20 = close_series.rolling(20).mean()
        std20 = close_series.rolling(20).std()
        upper_bb = sma20 + (2.0 * std20)
        lower_bb = sma20 - (2.0 * std20)
        bandwidth = (upper_bb - lower_bb) / sma20
        
        # Squeeze condition: bandwidth below 20th percentile of its 100-day history
        squeeze = bandwidth < bandwidth.rolling(100).quantile(0.20)
        breakout = (close_series > upper_bb.shift(1)) & squeeze.shift(1)
        sig = breakout.astype(int).rolling(3).max()
        return sig.fillna(0)

    # ----------------------------------------------------------------------------------
    # 5. ALPHA 5: SECTOR-RELATIVE RESIDUAL ALPHA
    # ----------------------------------------------------------------------------------
    def compute_alpha_sector_relative(self, stock_close: pd.Series, sector_close: pd.Series) -> pd.Series:
        """Stock 20-day return minus Sector ETF 20-day return (Residual Alpha)."""
        if sector_close is None or sector_close.empty:
            return pd.Series(0, index=stock_close.index)
        stock_ret20 = stock_close.pct_change(20)
        sector_ret20 = sector_close.pct_change(20).reindex(stock_close.index).ffill()
        residual = stock_ret20 - sector_ret20
        sig = (residual > 0.04).astype(int).rolling(5).max()
        return sig.fillna(0)

    # ----------------------------------------------------------------------------------
    # 6. ALPHA 6: INTRA-SECTOR PEER MEAN REVERSION
    # ----------------------------------------------------------------------------------
    def compute_alpha_peer_mean_reversion(self, stock_close: pd.Series, peer_closes_df: pd.DataFrame) -> pd.Series:
        """Stock 5-day drop relative to average 5-day return of closest industry peers."""
        if peer_closes_df.empty:
            return pd.Series(0, index=stock_close.index)
        stock_ret5 = stock_close.pct_change(5)
        peer_ret5_mean = peer_closes_df.pct_change(5).mean(axis=1).reindex(stock_close.index).ffill()
        peer_spread = stock_ret5 - peer_ret5_mean
        # Signal: stock dropped > 3% more than its peers
        sig = (peer_spread < -0.035).astype(int).rolling(2).max()
        return sig.fillna(0)

    # ----------------------------------------------------------------------------------
    # 7. GENERATE ALL 6 ALPHAS & INDEPENDENCE CORRELATION MATRIX
    # ----------------------------------------------------------------------------------
    def build_alpha_universe(self, symbol: str, stock_df: pd.DataFrame, sector_df: pd.DataFrame = None, peers_df: pd.DataFrame = None) -> dict:
        c = stock_df["close"].dropna()
        
        a1 = self.compute_alpha_12_1_momentum(c)
        a2 = self.compute_alpha_short_term_reversal(c)
        a3 = self.compute_alpha_trend_acceleration(c)
        a4 = self.compute_alpha_volatility_squeeze(c)
        a5 = self.compute_alpha_sector_relative(c, sector_df["close"] if sector_df is not None else None)
        a6 = self.compute_alpha_peer_mean_reversion(c, peers_df if peers_df is not None else pd.DataFrame())

        df_alphas = pd.DataFrame({
            "1. 12-1m Momentum": a1,
            "2. Short-Term Reversal": a2,
            "3. Trend Acceleration": a3,
            "4. Volatility Squeeze": a4,
            "5. Sector-Relative Alpha": a5,
            "6. Peer Mean Reversion": a6
        }).dropna()

        # Compute Pairwise Independence Correlation Matrix
        corr_matrix = df_alphas.corr()

        return {
            "symbol": symbol,
            "alphas_df": df_alphas,
            "correlation_matrix": corr_matrix
        }

if __name__ == "__main__":
    factory = AlphaFactory()
    conn = init_db(config.DB_PATH)
    
    # Load AMZN data
    df_amzn = conn.execute("SELECT timestamp::DATE as date, close FROM daily_bars WHERE symbol = 'AMZN' ORDER BY timestamp").fetchdf().set_index("date")
    
    res = factory.build_alpha_universe("AMZN", df_amzn)
    print("================================================================================")
    print("                 ALPHA INDEPENDENCE CORRELATION MATRIX (AMZN)")
    print("================================================================================")
    print(res["correlation_matrix"].round(3))
    print("\n[ORTHOGONALITY AUDIT]:")
    max_corr = res["correlation_matrix"].replace(1.0, np.nan).abs().max().max()
    print(f"  • Maximum Pairwise Correlation: {max_corr:.3f} (Constraint |rho| < 0.35: {'PASS' if max_corr < 0.35 else 'FAIL'})")
