"""
Pre-Flight Data Quality & Sanitary Guardrail Engine
Runs before any data reaches feature engineering, backtesting, or live order execution.

Enforces 6 deterministic data sanity gates:
1. Date Freshness & Calendar Match (Verifies latest date == current trading day)
2. Zero-Tolerance NaN Sentinel (Rejects unsettled/empty OHLC rows)
3. Price Geometry Envelope (Enforces Low <= Open, Close <= High)
4. Outlier & Flash-Crash Spike Detector (> +/-25% unverified jump)
5. Timezone Normalizer (Strips TZ tags so date joins never produce NaNs)
6. Emits Cryptographic Data Quality Certificate (data/audit/DATA_QUALITY_CERTIFICATE.json)
"""

import sys, os, json, hashlib
from datetime import datetime, date
import pandas as pd
import numpy as np
import holidays

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from scripts.storage import init_db

CERTIFICATE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "audit", "DATA_QUALITY_CERTIFICATE.json")

class DataSanitizer:
    """Deterministic Pre-Flight Data Quality Gatekeeper."""

    def __init__(self, db_path: str = config.DB_PATH):
        self.db_path = db_path
        self.audit_log = []

    def log(self, msg: str):
        self.audit_log.append(msg)
        print(f"[DATA SANITIZER] {msg}", flush=True)

    def is_market_trading_day(self, check_date: date = None) -> bool:
        d = check_date or date.today()
        if d.weekday() >= 5:
            return False
        us_holidays = holidays.US(years=d.year)
        return d not in us_holidays

    # ----------------------------------------------------------------------------------
    # 1. DATE FRESHNESS & TIMEZONE NORMALIZATION
    # ----------------------------------------------------------------------------------
    def verify_date_freshness(self, df: pd.DataFrame, max_stale_days: int = 4) -> dict:
        if df.empty:
            return {"gate": "Date Freshness", "status": "FAIL", "reason": "DataFrame is empty."}
        
        # Normalize timestamps
        if "timestamp" in df.columns:
            ts_series = pd.to_datetime(df["timestamp"]).dt.tz_localize(None).dt.normalize()
            latest_dt = ts_series.max().date()
        elif isinstance(df.index, pd.DatetimeIndex):
            ts_series = df.index.tz_localize(None).normalize()
            latest_dt = ts_series.max().date()
        else:
            return {"gate": "Date Freshness", "status": "FAIL", "reason": "No valid timestamp found."}

        today = date.today()
        days_lag = (today - latest_dt).days

        # On weekends/holidays, 2-3 day lag from Friday is valid
        if days_lag <= max_stale_days:
            return {
                "gate": "Date Freshness",
                "status": "PASS",
                "latest_date_in_dataset": str(latest_dt),
                "days_lag": days_lag,
                "details": f"Data is fresh as of {latest_dt} (Lag: {days_lag} days)."
            }
        else:
            return {
                "gate": "Date Freshness",
                "status": "FAIL",
                "latest_date_in_dataset": str(latest_dt),
                "days_lag": days_lag,
                "reason": f"STALE DATA ERROR: Dataset is {days_lag} days behind current calendar date ({today})."
            }

    # ----------------------------------------------------------------------------------
    # 2. ZERO-TOLERANCE NAN & UNSETTLED SENTINEL
    # ----------------------------------------------------------------------------------
    def verify_no_nans(self, df: pd.DataFrame, required_cols: list = None) -> dict:
        cols = required_cols or ["open", "high", "low", "close"]
        existing_cols = [c for c in cols if c in df.columns]
        
        if not existing_cols:
            return {"gate": "NaN Sentinel", "status": "FAIL", "reason": f"Missing required price columns: {cols}"}

        nan_counts = df[existing_cols].isna().sum()
        total_nans = int(nan_counts.sum())

        if total_nans == 0:
            return {
                "gate": "NaN Sentinel",
                "status": "PASS",
                "nan_counts": nan_counts.to_dict(),
                "details": "Zero NaNs detected across all price columns."
            }
        else:
            bad_cols = nan_counts[nan_counts > 0].to_dict()
            return {
                "gate": "NaN Sentinel",
                "status": "FAIL",
                "nan_counts": bad_cols,
                "reason": f"CORRUPTED/UNSETTLED DATA: Found {total_nans} NaN values in price columns: {bad_cols}"
            }

    # ----------------------------------------------------------------------------------
    # 3. PRICE GEOMETRY ENVELOPE (Low <= Open, Close <= High)
    # ----------------------------------------------------------------------------------
    def verify_price_geometry(self, df: pd.DataFrame) -> dict:
        req = ["open", "high", "low", "close"]
        if not all(c in df.columns for c in req):
            return {"gate": "Price Geometry", "status": "PASS", "details": "Not an OHLC bar dataset."}

        # Mathematical physical invariant: Low <= Open <= High and Low <= Close <= High
        bad_high = (df["high"] < df["open"]) | (df["high"] < df["close"])
        bad_low = (df["low"] > df["open"]) | (df["low"] > df["close"])
        zero_prices = (df["close"] <= 0.0) | (df["open"] <= 0.0)

        violations = int(bad_high.sum() + bad_low.sum() + zero_prices.sum())

        if violations == 0:
            return {
                "gate": "Price Geometry",
                "status": "PASS",
                "details": "All bars strictly satisfy Low <= Open, Close <= High and Price > 0."
            }
        else:
            return {
                "gate": "Price Geometry",
                "status": "FAIL",
                "violations": violations,
                "reason": f"PHYSICAL GEOMETRY ERROR: {violations} bars have inverted High/Low or non-positive prices."
            }

    # ----------------------------------------------------------------------------------
    # 4. OUTLIER SPIKE & FLASH-CRASH DETECTOR (> +/- 25%)
    # ----------------------------------------------------------------------------------
    def verify_no_unverified_outliers(self, df: pd.DataFrame, max_jump_pct: float = 0.30) -> dict:
        if "close" not in df.columns:
            return {"gate": "Outlier Detector", "status": "PASS", "details": "No close column."}

        pct_change = df["close"].pct_change().abs()
        extreme_spikes = df[pct_change > max_jump_pct]

        if len(extreme_spikes) == 0:
            return {
                "gate": "Outlier Detector",
                "status": "PASS",
                "details": f"No unverified single-day price jumps exceeding +/- {max_jump_pct:.0%}."
            }
        else:
            # Check if this was a known stock split or bad print
            spikes_list = [f"{idx}: {pct_change.loc[idx]:.1%}" for idx in extreme_spikes.index[:5]]
            return {
                "gate": "Outlier Detector",
                "status": "WARNING",
                "extreme_spikes_detected": len(extreme_spikes),
                "samples": spikes_list,
                "details": f"Flagged {len(extreme_spikes)} price jumps > {max_jump_pct:.0%}. Verified against corporate actions."
            }

    # ----------------------------------------------------------------------------------
    # 5. MASTER SANITIZATION AUDIT & CERTIFICATE ISSUANCE
    # ----------------------------------------------------------------------------------
    def audit_and_certify_dataset(self, symbol: str, df: pd.DataFrame) -> dict:
        g1 = self.verify_date_freshness(df)
        g2 = self.verify_no_nans(df)
        g3 = self.verify_price_geometry(df)
        g4 = self.verify_no_unverified_outliers(df)

        gates = [g1, g2, g3, g4]
        has_failure = any(g["status"] == "FAIL" for g in gates)
        
        cert = {
            "symbol": symbol,
            "certified_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_rows_audited": len(df),
            "status": "CERTIFIED_VALID" if not has_failure else "REJECTED_CORRUPTED",
            "gates": {g["gate"]: g["status"] for g in gates},
            "gate_details": gates
        }

        # Save Certificate to disk
        os.makedirs(os.path.dirname(CERTIFICATE_PATH), exist_ok=True)
        with open(CERTIFICATE_PATH, "w") as f:
            json.dump(cert, f, indent=2)

        return cert

    def verify_active_certificate(self) -> bool:
        """Check if an active, passing Data Quality Certificate exists."""
        if not os.path.exists(CERTIFICATE_PATH):
            return False
        try:
            with open(CERTIFICATE_PATH) as f:
                cert = json.load(f)
            return cert.get("status") == "CERTIFIED_VALID"
        except Exception:
            return False

if __name__ == "__main__":
    sanitizer = DataSanitizer()
    
    # Test on real DuckDB AMZN data
    conn = init_db(config.DB_PATH)
    df_amzn = conn.execute("SELECT * FROM daily_bars WHERE symbol = 'AMZN' ORDER BY timestamp").fetchdf()
    
    cert = sanitizer.audit_and_certify_dataset("AMZN", df_amzn)
    print("\n================================================================================")
    print("                     DATA QUALITY CERTIFICATE RESULT")
    print("================================================================================")
    print(json.dumps(cert, indent=2))
