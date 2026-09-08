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
from datetime import datetime, date

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

PYTHON = os.path.join(PROJECT_DIR, "venv", "Scripts", "python.exe")
if not os.path.exists(PYTHON):
    PYTHON = os.path.join(PROJECT_DIR, "venv", "bin", "python")


# --- Market holiday check ---

# US stock market holidays (fixed + observed rules)
# Source: NYSE holiday calendar
def get_market_holidays(year: int) -> set:
    """Return set of date objects for US market holidays in a given year."""
    from datetime import timedelta
    holidays = set()

    # New Year's Day (Jan 1, observed Fri if Sat, Mon if Sun)
    holidays.add(_observed(date(year, 1, 1)))

    # MLK Day (3rd Monday of January)
    holidays.add(_nth_weekday(year, 1, 0, 3))  # 0=Monday, 3rd occurrence

    # Presidents' Day (3rd Monday of February)
    holidays.add(_nth_weekday(year, 2, 0, 3))

    # Good Friday (2 days before Easter Sunday)
    holidays.add(_easter(year) - timedelta(days=2))

    # Memorial Day (last Monday of May)
    holidays.add(_last_weekday(year, 5, 0))

    # Juneteenth (June 19, observed)
    holidays.add(_observed(date(year, 6, 19)))

    # Independence Day (July 4, observed)
    holidays.add(_observed(date(year, 7, 4)))

    # Labor Day (1st Monday of September)
    holidays.add(_nth_weekday(year, 9, 0, 1))

    # Thanksgiving (4th Thursday of November)
    holidays.add(_nth_weekday(year, 11, 3, 4))  # 3=Thursday, 4th occurrence

    # Christmas (Dec 25, observed)
    holidays.add(_observed(date(year, 12, 25)))

    return holidays


def _observed(d: date) -> date:
    """If holiday falls on Sat, observe Fri. If Sun, observe Mon."""
    from datetime import timedelta
    if d.weekday() == 5:  # Saturday
        return d - timedelta(days=1)
    elif d.weekday() == 6:  # Sunday
        return d + timedelta(days=1)
    return d


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """Return the nth occurrence of a weekday in a given month."""
    import calendar
    cal = calendar.monthcalendar(year, month)
    count = 0
    for week in cal:
        if week[weekday] != 0:
            count += 1
            if count == n:
                return date(year, month, week[weekday])
    raise ValueError(f"Could not find {n}th weekday {weekday} in {year}-{month}")


def _last_weekday(year: int, month: int, weekday: int) -> date:
    """Return the last occurrence of a weekday in a given month."""
    import calendar
    cal = calendar.monthcalendar(year, month)
    for week in reversed(cal):
        if week[weekday] != 0:
            return date(year, month, week[weekday])
    raise ValueError(f"Could not find last weekday {weekday} in {year}-{month}")


def _easter(year: int) -> date:
    """Compute Easter Sunday using the Anonymous Gregorian algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def is_market_open(d: date = None) -> bool:
    """Check if the US stock market is open on a given date."""
    if d is None:
        d = date.today()
    # Weekends
    if d.weekday() >= 5:
        return False
    # Holidays
    if d in get_market_holidays(d.year):
        return False
    return True

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
    force = "--force" in sys.argv
    today = datetime.now().strftime("%Y-%m-%d")

    # Skip if market is closed (weekends + holidays), unless --force
    if not force and not is_market_open(date.today()):
        msg = f"Market closed today ({date.today().strftime('%A %Y-%m-%d')}). Skipping. Use --force to override."
        print(msg)
        # Still write a minimal report so there's a record
        os.makedirs(REPORTS_DIR, exist_ok=True)
        with open(os.path.join(REPORTS_DIR, f"daily_{today}.txt"), "w") as f:
            f.write(f"DAILY RESEARCH REPORT: {today}\nMarket closed (holiday/weekend). Skipped.\n")
        return
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
