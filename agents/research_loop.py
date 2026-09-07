"""
Research Loop: daily orchestrator for the AI research system.
Chains: data update -> features -> regime -> scout -> signals -> paper trade -> log.

Usage:
    python agents/research_loop.py              # Full loop, dry run
    python agents/research_loop.py --execute    # Full loop, submit orders
    python agents/research_loop.py --review     # Run weekly governor review only
    python agents/research_loop.py --experiment # Run hypothesis through Experimenter -> Skeptic -> Gatekeeper
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
from agents.experimenter import run_experiment
from agents.skeptic import evaluate_experiment
from agents.gatekeeper import promote_strategy


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


def experiment_loop(strategy_name: str = None, symbols: list = None):
    """
    Run hypothesis through the full agent pipeline:
    Experimenter -> Skeptic -> Gatekeeper
    """
    from scripts.signal_generator import (
        strategy_mr_vix_tuned, strategy_momentum, strategy_mean_reversion,
        strategy_mr_regime, strategy_momentum_regime,
    )

    STRATEGIES = {
        "mr_vix_tuned": strategy_mr_vix_tuned,
        "momentum": strategy_momentum,
        "mean_reversion": strategy_mean_reversion,
        "mr_regime": strategy_mr_regime,
        "momentum_regime": strategy_momentum_regime,
    }

    if strategy_name and strategy_name not in STRATEGIES:
        print(f"Unknown strategy: {strategy_name}")
        print(f"Available: {list(STRATEGIES.keys())}")
        return

    strategies = {strategy_name: STRATEGIES[strategy_name]} if strategy_name else STRATEGIES
    test_symbols = symbols or ["AMZN", "NVDA", "AMD", "TSLA", "AAPL"]

    print(f"{'#'*60}")
    print(f"# EXPERIMENT LOOP: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"# Strategies: {list(strategies.keys())}")
    print(f"# Symbols: {test_symbols}")
    print(f"{'#'*60}")

    conn = init_db(config.DB_PATH)
    approved = []
    rejected = []

    for strat_name, strat_fn in strategies.items():
        for symbol in test_symbols:
            print(f"\n--- {strat_name} on {symbol} ---")

            # Step 1: Experimenter
            print(f"  Experimenter: running backtest...")
            exp_result = run_experiment(conn, strat_fn, strat_name, symbol)
            print(f"  OOS Sharpe: {exp_result.get('oos_sharpe', 0):.2f}, Verdict: {exp_result.get('skeptic_verdict', 'N/A')}")

            # Step 2: Skeptic
            print(f"  Skeptic: evaluating...")
            skeptic_eval = evaluate_experiment(conn, exp_result)
            print(f"  Skeptic verdict: {skeptic_eval['verdict']} ({skeptic_eval.get('pass_count', 0)}/5)")

            # Step 3: Gatekeeper (only if Skeptic doesn't reject)
            if skeptic_eval["verdict"] != "REJECT":
                print(f"  Gatekeeper: reviewing for promotion...")
                gate_result = promote_strategy(conn, skeptic_eval)
                print(f"  Gatekeeper: {gate_result['decision']} — {gate_result['reason']}")
                if gate_result["decision"] in ("APPROVE", "APPROVE_REDUCED"):
                    approved.append(f"{strat_name} on {symbol}")
                else:
                    rejected.append(f"{strat_name} on {symbol}: {gate_result['decision']}")
            else:
                rejected.append(f"{strat_name} on {symbol}: Skeptic REJECT")
                print(f"  Skeptic rejected — skipping Gatekeeper.")

    conn.close()

    print(f"\n{'#'*60}")
    print(f"# RESULTS")
    print(f"#  Approved: {len(approved)}")
    for a in approved:
        print(f"#    + {a}")
    print(f"#  Rejected: {len(rejected)}")
    for r in rejected:
        print(f"#    - {r}")
    print(f"{'#'*60}")


if __name__ == "__main__":
    if "--review" in sys.argv:
        weekly_review()
    elif "--experiment" in sys.argv:
        # Optional: --strategy=mr_vix_tuned --symbols=AMZN,NVDA
        strat = None
        syms = None
        for arg in sys.argv:
            if arg.startswith("--strategy="):
                strat = arg.split("=", 1)[1]
            elif arg.startswith("--symbols="):
                syms = arg.split("=", 1)[1].split(",")
        experiment_loop(strat, syms)
    else:
        execute = "--execute" in sys.argv
        daily_loop(execute)
