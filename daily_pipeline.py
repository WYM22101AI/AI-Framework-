"""
Daily Pipeline: run the complete data -> features -> signals -> paper trade cycle.
Designed to run daily after market close (5:00 PM ET).

Usage:
    python daily_pipeline.py              # Full pipeline, dry run for trades
    python daily_pipeline.py --execute    # Full pipeline, submit orders to Alpaca
"""

import sys
import os
import subprocess
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON = os.path.join(PROJECT_DIR, "venv", "Scripts", "python.exe")
if not os.path.exists(PYTHON):
    PYTHON = os.path.join(PROJECT_DIR, "venv", "bin", "python")  # Mac/Linux


def run_step(name, script, args=None):
    """Run a pipeline step and report status."""
    print(f"\n{'='*60}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {name}")
    print(f"{'='*60}")

    cmd = [PYTHON, os.path.join(PROJECT_DIR, script)]
    if args:
        cmd.extend(args)

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_DIR)

    if result.stdout:
        print(result.stdout)
    if result.returncode != 0:
        print(f"WARNING: {name} returned exit code {result.returncode}")
        if result.stderr:
            # Only show last few lines of stderr
            lines = result.stderr.strip().split("\n")
            for line in lines[-5:]:
                print(f"  {line}")
        return False
    return True


def main():
    execute = "--execute" in sys.argv

    print(f"{'#'*60}")
    print(f"# DAILY PIPELINE: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"# Mode: {'LIVE EXECUTION' if execute else 'DRY RUN'}")
    print(f"{'#'*60}")

    # Step 1: Update market data (all sources)
    run_step("Step 1: Update Market Data", "update_market_data.py")

    # Step 2: Compute features
    run_step("Step 2: Compute Features", os.path.join("scripts", "feature_engine.py"))

    # Step 3: Paper trading
    trade_args = ["--execute"] if execute else []
    run_step("Step 3: Paper Trading", os.path.join("scripts", "paper_trader.py"), trade_args)

    print(f"\n{'#'*60}")
    print(f"# PIPELINE COMPLETE: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'#'*60}")


if __name__ == "__main__":
    main()
