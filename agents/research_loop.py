"""
Research Loop: daily orchestrator for the AI research system.
Chains: data update -> features -> regime -> scout -> signals -> paper trade -> log.

Usage:
    python agents/research_loop.py              # Full loop, dry run
    python agents/research_loop.py --execute    # Full loop, submit orders
    python agents/research_loop.py --review     # Run weekly governor review only
"""

import sys
import os
import subprocess
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

import duckdb
import config
from scripts.storage import init_db
from agents.regime import get_current_regime
from agents.scout import scan_anomalies
from agents.governor import run_weekly_review


PYTHON = os.path.join(PROJECT_DIR, "venv", "Scripts", "python.exe")
if not os.path.exists(PYTHON):
    PYTHON = os.path.join(PROJECT_DIR, "venv", "bin", "python")


def run_script(name, script):
    """Run a Python script and report status."""
    print(f"\n  [{datetime.now().strftime('%H:%M:%S')}] {name}...")
    cmd = [PYTHON, os.path.join(PROJECT_DIR, script)]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_DIR)
    if result.returncode != 0:
        print(f"    WARNING: {name} failed")
        if result.stderr:
            for line in result.stderr.strip().split("\n")[-3:]:
                print(f"    {line}")
        return False
    return True


def daily_loop(execute=False):
    """Run the full daily research loop."""
    print(f"{'#'*60}")
    print(f"# RESEARCH LOOP: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"# Mode: {'EXECUTE' if execute else 'DRY RUN'}")
    print(f"{'#'*60}")

    # Step 1: Update data
    print("\n=== STEP 1: Update Market Data ===")
    run_script("Data update", "update_market_data.py")

    # Step 2: Compute features
    print("\n=== STEP 2: Compute Features ===")
    run_script("Features", os.path.join("scripts", "feature_engine.py"))

    # Step 3: Classify regime
    print("\n=== STEP 3: Market Regime ===")
    conn = init_db(config.DB_PATH)

    regime_result = get_current_regime(conn)
    print(f"  Regime: {regime_result['regime']}")
    print(f"  {regime_result['description']}")

    # Log regime
    from agents.base import BaseAgent
    regime_agent = BaseAgent("regime", "")
    regime_agent.log(conn, "classify", "Daily regime classification", regime_result, regime_result["regime"])

    # Step 4: Scout for anomalies
    print("\n=== STEP 4: Scout Anomalies ===")
    scout_result = scan_anomalies(conn)
    print(f"  {scout_result['summary']}")

    if scout_result["anomalies"]:
        for a in scout_result["anomalies"][:5]:  # Show top 5
            print(f"    {a['symbol']}: {', '.join(a['flags'])}")

    scout_agent = BaseAgent("scout", "")
    scout_agent.log(conn, "scan", "Daily anomaly scan", scout_result, regime_result["regime"])

    conn.close()

    # Step 5: Paper trading
    print("\n=== STEP 5: Paper Trading ===")
    trade_args = ["--execute"] if execute else []
    trade_script = os.path.join("scripts", "paper_trader.py")
    if trade_args:
        cmd = [PYTHON, os.path.join(PROJECT_DIR, trade_script)] + trade_args
        subprocess.run(cmd, cwd=PROJECT_DIR)
    else:
        run_script("Paper trader (dry run)", trade_script)

    # Step 6: Summary
    print(f"\n{'#'*60}")
    print(f"# LOOP COMPLETE: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"# Regime: {regime_result['regime']}")
    print(f"# Anomalies: {scout_result['anomaly_count']}")
    print(f"{'#'*60}")


def weekly_review():
    """Run the governor's weekly review."""
    print(f"{'#'*60}")
    print(f"# WEEKLY REVIEW: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"{'#'*60}")

    conn = init_db(config.DB_PATH)
    result = run_weekly_review(conn)
    conn.close()

    print(f"\nFindings:")
    for f in result["findings"]:
        print(f"  - {f}")

    print(f"\nRecommendations:")
    for r in result["recommendations"]:
        print(f"  - {r}")

    print(f"\nStatus: {result['status']}")


if __name__ == "__main__":
    if "--review" in sys.argv:
        weekly_review()
    else:
        execute = "--execute" in sys.argv
        daily_loop(execute)
