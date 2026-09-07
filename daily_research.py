"""
Daily Research Job: scheduled task that runs after market close.

Runs the full agent pipeline:
1. Update market data (stocks, FRED, earnings, SEC, news)
2. Compute features (19 per stock per day)
3. Classify market regime (VIX + SPY)
4. Scout for anomalies (volume, RSI, Bollinger, earnings)
5. Generate trading signals and paper trade (dry run by default)
6. Save a daily report to data/reports/

Usage:
    python daily_research.py              # Dry run (no orders)
    python daily_research.py --execute    # Submit orders to Alpaca

Designed to run via Windows Task Scheduler at 5:30 PM ET (after market close).
"""

import sys
import os
import subprocess
import json
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

PYTHON = os.path.join(PROJECT_DIR, "venv", "Scripts", "python.exe")
if not os.path.exists(PYTHON):
    PYTHON = os.path.join(PROJECT_DIR, "venv", "bin", "python")

REPORTS_DIR = os.path.join(PROJECT_DIR, "data", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


def run_script(name, script):
    """Run a Python script, return (success, duration_seconds)."""
    start = datetime.now()
    cmd = [PYTHON, os.path.join(PROJECT_DIR, script)]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_DIR)
    elapsed = (datetime.now() - start).total_seconds()
    success = result.returncode == 0
    error = ""
    if not success and result.stderr:
        error = result.stderr.strip().split("\n")[-1]
    return success, elapsed, error


def main():
    execute = "--execute" in sys.argv
    today = datetime.now().strftime("%Y-%m-%d")
    start_time = datetime.now()

    report = {
        "date": today,
        "start_time": start_time.strftime("%H:%M:%S"),
        "mode": "EXECUTE" if execute else "DRY_RUN",
        "steps": {},
        "regime": None,
        "anomalies": [],
        "opportunities": [],
        "errors": [],
    }

    # Step 1: Update market data
    ok, dur, err = run_script("Data update", "update_market_data.py")
    report["steps"]["data_update"] = {"ok": ok, "seconds": dur}
    if not ok:
        report["errors"].append(f"Data update failed: {err}")

    # Step 2: Compute features
    ok, dur, err = run_script("Features", os.path.join("scripts", "feature_engine.py"))
    report["steps"]["features"] = {"ok": ok, "seconds": dur}
    if not ok:
        report["errors"].append(f"Feature computation failed: {err}")

    # Step 3: Agents (regime + scout)
    import config
    from scripts.storage import init_db
    from agents.regime import get_current_regime
    from agents.scout import scan_anomalies
    from agents.base import BaseAgent

    conn = init_db(config.DB_PATH)

    try:
        regime = get_current_regime(conn)
        report["regime"] = {
            "classification": regime["regime"],
            "description": regime["description"],
            "vix": regime.get("vix"),
        }
        # Log regime
        agent = BaseAgent("regime", "")
        agent.log(conn, "classify", "Scheduled daily classification", regime, regime["regime"])
    except Exception as e:
        report["errors"].append(f"Regime agent failed: {e}")

    try:
        scout = scan_anomalies(conn)
        report["anomalies"] = scout.get("anomalies", [])

        # Identify opportunities: stocks with 2+ flags including oversold signals
        for anomaly in scout.get("anomalies", []):
            flags_text = " ".join(anomaly["flags"]).lower()
            if any(kw in flags_text for kw in ["oversold", "below bollinger", "big move down"]):
                report["opportunities"].append({
                    "symbol": anomaly["symbol"],
                    "flags": anomaly["flags"],
                    "type": "potential_mean_reversion",
                })
            elif any(kw in flags_text for kw in ["volume", "overbought", "big move up"]):
                report["opportunities"].append({
                    "symbol": anomaly["symbol"],
                    "flags": anomaly["flags"],
                    "type": "unusual_activity",
                })

        agent = BaseAgent("scout", "")
        agent.log(conn, "scan", "Scheduled daily scan", scout, report.get("regime", {}).get("classification"))
    except Exception as e:
        report["errors"].append(f"Scout agent failed: {e}")

    conn.close()

    # Step 4: Paper trading
    trade_script = os.path.join("scripts", "paper_trader.py")
    trade_args = ["--execute"] if execute else []
    cmd = [PYTHON, os.path.join(PROJECT_DIR, trade_script)] + trade_args
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_DIR)
    report["steps"]["paper_trading"] = {"ok": result.returncode == 0, "output": result.stdout[:500]}
    if result.returncode != 0:
        report["errors"].append(f"Paper trading failed: {result.stderr.strip().split(chr(10))[-1] if result.stderr else 'unknown'}")

    # Finalize
    end_time = datetime.now()
    report["end_time"] = end_time.strftime("%H:%M:%S")
    report["total_seconds"] = (end_time - start_time).total_seconds()
    report["status"] = "OK" if not report["errors"] else "ERRORS"

    # Save JSON report
    report_file = os.path.join(REPORTS_DIR, f"daily_{today}.json")
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Save human-readable summary
    summary_file = os.path.join(REPORTS_DIR, f"daily_{today}.txt")
    with open(summary_file, "w") as f:
        f.write(f"DAILY RESEARCH REPORT: {today}\n")
        f.write(f"{'='*50}\n\n")
        f.write(f"Mode: {report['mode']}\n")
        f.write(f"Duration: {report['total_seconds']:.0f}s\n")
        f.write(f"Status: {report['status']}\n\n")

        if report["regime"]:
            f.write(f"MARKET REGIME: {report['regime']['classification']}\n")
            f.write(f"  {report['regime']['description']}\n\n")

        if report["opportunities"]:
            f.write(f"OPPORTUNITIES ({len(report['opportunities'])}):\n")
            for opp in report["opportunities"]:
                f.write(f"  {opp['symbol']} [{opp['type']}]: {', '.join(opp['flags'])}\n")
            f.write("\n")
        else:
            f.write("OPPORTUNITIES: None today.\n\n")

        if report["anomalies"]:
            f.write(f"ALL ANOMALIES ({len(report['anomalies'])}):\n")
            for a in report["anomalies"]:
                f.write(f"  {a['symbol']}: {', '.join(a['flags'])}\n")
            f.write("\n")

        if report["errors"]:
            f.write(f"ERRORS ({len(report['errors'])}):\n")
            for e in report["errors"]:
                f.write(f"  {e}\n")

    # Print summary to stdout (for logs)
    with open(summary_file) as f:
        print(f.read())

    print(f"\nReports saved to:\n  {report_file}\n  {summary_file}")


if __name__ == "__main__":
    main()
