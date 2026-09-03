"""
Backtesting Engine: test trading signals against historical data.
Produces performance metrics with proper methodology.

Design rules:
- Entry at next day's OPEN (not today's close — that's look-ahead)
- Include transaction costs (default 0.05% round-trip = 5 bps)
- Walk-forward: in-sample vs out-of-sample split
- Compare vs SPY buy-and-hold benchmark

Usage:
    from scripts.backtester import run_backtest
    results = run_backtest(signal, prices, "momentum")
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import duckdb
import config
from scripts.stats_engine import full_skeptic_report


def get_prices(conn, symbol: str) -> pd.DataFrame:
    """Get daily OHLC prices for a symbol."""
    return conn.execute(f"""
        SELECT timestamp::DATE as date, open, close
        FROM daily_bars
        WHERE symbol = '{symbol}'
        ORDER BY timestamp
    """).fetchdf()


def compute_strategy_returns(
    signal: pd.Series,
    prices: pd.DataFrame,
    cost_per_trade: float = 0.0005,
) -> pd.DataFrame:
    """
    Compute daily strategy returns from a signal.

    signal: indexed by date, values in {-1, 0, 1}
    prices: DataFrame with 'date', 'open', 'close' columns
    cost_per_trade: round-trip cost as fraction (default 0.05%)

    Execution model:
    - Signal generated at close of day T
    - Execute at open of day T+1
    - Measure return from open T+1 to open T+2 (or close T+1 for simplicity)
    """
    prices = prices.set_index("date").sort_index()

    # Next-day return: open-to-close (signal at close T, enter at open T+1)
    prices["next_open"] = prices["open"].shift(-1)
    prices["next_close"] = prices["close"].shift(-1)
    prices["forward_return"] = (prices["next_close"] - prices["next_open"]) / prices["next_open"]

    # Align signal with prices
    result = pd.DataFrame(index=prices.index)
    result["forward_return"] = prices["forward_return"]
    result["signal"] = signal.reindex(prices.index).fillna(0)

    # Strategy return = signal * forward_return - costs on trade days
    result["position_change"] = result["signal"].diff().abs()
    result["cost"] = result["position_change"] * cost_per_trade
    result["strategy_return"] = result["signal"] * result["forward_return"] - result["cost"]

    # Benchmark: buy and hold
    result["benchmark_return"] = prices["forward_return"]

    result = result.dropna()
    return result


def compute_metrics(returns: pd.Series, name: str = "") -> dict:
    """Compute standard performance metrics for a return series."""
    if len(returns) < 20:
        return {"name": name, "error": "insufficient data"}

    total_return = (1 + returns).prod() - 1
    n_days = len(returns)
    calendar_days = n_days * 365 / 252  # approximate
    annualized_return = (1 + total_return) ** (365 / calendar_days) - 1 if calendar_days > 0 else 0

    daily_std = returns.std()
    sharpe = (returns.mean() / daily_std * np.sqrt(252)) if daily_std > 0 else 0

    # Max drawdown
    cumulative = (1 + returns).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    max_drawdown = float(drawdown.min())

    # Win rate
    non_zero = returns[returns != 0]
    win_rate = float((non_zero > 0).mean()) if len(non_zero) > 0 else 0

    # Average win / average loss
    wins = non_zero[non_zero > 0]
    losses = non_zero[non_zero < 0]
    avg_win = float(wins.mean()) if len(wins) > 0 else 0
    avg_loss = float(losses.mean()) if len(losses) > 0 else 0
    profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float("inf")

    return {
        "name": name,
        "total_return": float(total_return),
        "annualized_return": float(annualized_return),
        "sharpe_ratio": float(sharpe),
        "max_drawdown": float(max_drawdown),
        "win_rate": float(win_rate),
        "avg_win": float(avg_win),
        "avg_loss": float(avg_loss),
        "profit_factor": float(profit_factor),
        "n_days": n_days,
        "n_trades": int(non_zero.count()),
    }


def run_backtest(
    signal: pd.Series,
    prices: pd.DataFrame,
    strategy_name: str = "unnamed",
    cost_per_trade: float = 0.0005,
    split_date: str = "2023-01-01",
) -> dict:
    """
    Run a full backtest with in-sample / out-of-sample split.

    signal: Series indexed by date, values {-1, 0, 1}
    prices: DataFrame with date, open, close
    strategy_name: label
    cost_per_trade: round-trip cost (default 5 bps)
    split_date: boundary between in-sample and out-of-sample

    Returns dict with metrics for both periods + Skeptic report on OOS.
    """
    result = compute_strategy_returns(signal, prices, cost_per_trade)

    split = pd.Timestamp(split_date)
    in_sample = result[result.index < split]
    out_sample = result[result.index >= split]

    # Metrics
    is_metrics = compute_metrics(in_sample["strategy_return"], f"{strategy_name} (in-sample)")
    oos_metrics = compute_metrics(out_sample["strategy_return"], f"{strategy_name} (out-of-sample)")
    bench_metrics = compute_metrics(result["benchmark_return"], "SPY buy-and-hold")

    # Run Skeptic on out-of-sample only (the honest test)
    skeptic = full_skeptic_report(
        out_sample["signal"],
        out_sample["forward_return"],
        strategy_name=f"{strategy_name} (OOS)",
        transaction_cost=cost_per_trade,
    )

    # Overfitting check: compare IS vs OOS Sharpe
    is_sharpe = is_metrics.get("sharpe_ratio", 0)
    oos_sharpe = oos_metrics.get("sharpe_ratio", 0)
    overfit_warning = (is_sharpe > 2 * oos_sharpe) if oos_sharpe != 0 else (is_sharpe > 1)

    return {
        "strategy": strategy_name,
        "split_date": split_date,
        "in_sample": is_metrics,
        "out_of_sample": oos_metrics,
        "benchmark": bench_metrics,
        "skeptic_report": skeptic,
        "overfit_warning": overfit_warning,
        "beats_benchmark": oos_metrics.get("annualized_return", 0) > bench_metrics.get("annualized_return", 0),
    }


def print_backtest_report(result: dict):
    """Pretty-print a backtest result."""
    print(f"\n{'='*60}")
    print(f"BACKTEST REPORT: {result['strategy']}")
    print(f"Split date: {result['split_date']}")
    print(f"{'='*60}")

    for period_key, label in [("in_sample", "IN-SAMPLE"), ("out_of_sample", "OUT-OF-SAMPLE"), ("benchmark", "BENCHMARK (SPY B&H)")]:
        m = result[period_key]
        print(f"\n--- {label} ---")
        print(f"  Total return:     {m['total_return']*100:+.1f}%")
        print(f"  Annualized:       {m['annualized_return']*100:+.1f}%")
        print(f"  Sharpe ratio:     {m['sharpe_ratio']:.2f}")
        print(f"  Max drawdown:     {m['max_drawdown']*100:.1f}%")
        print(f"  Win rate:         {m['win_rate']*100:.0f}%")
        print(f"  Trades:           {m['n_trades']}")

    sr = result["skeptic_report"]
    print(f"\n--- SKEPTIC VERDICT (out-of-sample) ---")
    print(f"  t-test:           p={sr['t_test']['p_value']:.4f}  {'PASS' if sr['t_test']['significant'] else 'FAIL'}")
    print(f"  Bootstrap:        {'PASS' if not sr['bootstrap'].get('zero_in_ci', True) else 'FAIL'}")
    print(f"  Permutation:      p={sr['permutation']['p_value']:.4f}  {'PASS' if sr['permutation']['significant'] else 'FAIL'}")
    print(f"  Walk-forward:     {sr['walk_forward']['positive_folds']}/{sr['walk_forward']['total_folds']} positive  {'PASS' if sr['walk_forward']['consistent'] else 'FAIL'}")
    print(f"  Economic sig:     {'PASS' if sr['economic_significance']['survives_costs'] else 'FAIL'}")
    print(f"  VERDICT:          {sr['verdict']} ({sr['tests_passed']}/{sr['tests_total']})")

    if result["overfit_warning"]:
        print(f"\n  WARNING: Possible overfitting (IS Sharpe >> OOS Sharpe)")

    if result["beats_benchmark"]:
        print(f"\n  Beats SPY buy-and-hold out-of-sample: YES")
    else:
        print(f"\n  Beats SPY buy-and-hold out-of-sample: NO")
