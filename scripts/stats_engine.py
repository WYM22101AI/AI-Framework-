"""
Statistics Engine: rigorous statistical tests for the Skeptic.
These are the tools that determine whether a trading signal is real or noise.

ALL calculations are deterministic Python — LLMs never compute statistics.

Usage:
    from scripts.stats_engine import *
    result = t_test_returns(returns_series)
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Optional


def t_test_returns(returns: pd.Series) -> dict:
    """
    Test whether mean return is significantly different from zero.
    Returns: mean, t_stat, p_value, n, significant (at 0.05)
    """
    clean = returns.dropna()
    if len(clean) < 10:
        return {"mean": None, "t_stat": None, "p_value": None, "n": len(clean), "significant": False}

    t_stat, p_value = stats.ttest_1samp(clean, 0)

    return {
        "mean": float(clean.mean()),
        "t_stat": float(t_stat),
        "p_value": float(p_value),
        "n": len(clean),
        "significant": p_value < 0.05,
    }


def bootstrap_confidence_interval(returns: pd.Series, n_samples: int = 10000, ci: float = 0.95) -> dict:
    """
    Bootstrap confidence interval for mean return.
    Returns: mean, ci_lower, ci_upper, se
    """
    clean = returns.dropna().values
    if len(clean) < 10:
        return {"mean": None, "ci_lower": None, "ci_upper": None, "se": None}

    boot_means = np.array([
        np.mean(np.random.choice(clean, size=len(clean), replace=True))
        for _ in range(n_samples)
    ])

    alpha = (1 - ci) / 2
    ci_lower = float(np.percentile(boot_means, alpha * 100))
    ci_upper = float(np.percentile(boot_means, (1 - alpha) * 100))

    return {
        "mean": float(np.mean(clean)),
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "se": float(np.std(boot_means)),
        "zero_in_ci": ci_lower <= 0 <= ci_upper,
    }


def permutation_test(signal: pd.Series, returns: pd.Series, n_perms: int = 5000) -> dict:
    """
    Permutation test: shuffle signal labels, recompute mean return.
    Tests whether the signal-return relationship is real.

    signal: 1 (long), -1 (short), 0 (no position)
    returns: next-day returns

    Returns: real_mean, p_value, pct_beat (what % of shuffles beat the real metric)
    """
    aligned = pd.DataFrame({"signal": signal, "ret": returns}).dropna()
    aligned = aligned[aligned["signal"] != 0]

    if len(aligned) < 20:
        return {"real_mean": None, "p_value": None, "pct_beat": None, "n": len(aligned)}

    # Real strategy return: signal * next-day return
    strategy_returns = aligned["signal"] * aligned["ret"]
    real_mean = strategy_returns.mean()

    # Shuffle signal labels and recompute
    signals_array = aligned["signal"].values
    returns_array = aligned["ret"].values
    perm_means = np.zeros(n_perms)

    for i in range(n_perms):
        shuffled = np.random.permutation(signals_array)
        perm_means[i] = (shuffled * returns_array).mean()

    # What fraction of shuffled results beat the real result?
    pct_beat = float(np.mean(perm_means >= real_mean))

    return {
        "real_mean": float(real_mean),
        "p_value": pct_beat,  # one-sided: fraction of perms that beat real
        "pct_beat": pct_beat,
        "n": len(aligned),
        "significant": pct_beat < 0.05,
    }


def walk_forward_test(signal: pd.Series, returns: pd.Series, n_folds: int = 5) -> dict:
    """
    Walk-forward (rolling out-of-sample) test.
    Splits data into n_folds sequential periods and tests each.

    Returns: per-fold Sharpe ratios, overall consistency
    """
    aligned = pd.DataFrame({"signal": signal, "ret": returns}).dropna()
    aligned = aligned[aligned["signal"] != 0]

    if len(aligned) < n_folds * 20:
        return {"folds": [], "consistent": False, "n": len(aligned)}

    fold_size = len(aligned) // n_folds
    folds = []

    for i in range(n_folds):
        start = i * fold_size
        end = start + fold_size if i < n_folds - 1 else len(aligned)
        fold_data = aligned.iloc[start:end]

        strat_ret = fold_data["signal"] * fold_data["ret"]
        mean_ret = strat_ret.mean()
        std_ret = strat_ret.std()
        sharpe = (mean_ret / std_ret * np.sqrt(252)) if std_ret > 0 else 0

        folds.append({
            "fold": i + 1,
            "n": len(fold_data),
            "mean_return": float(mean_ret),
            "sharpe": float(sharpe),
            "positive": mean_ret > 0,
        })

    # Consistent = positive in at least 60% of folds
    positive_folds = sum(1 for f in folds if f["positive"])
    consistent = positive_folds >= n_folds * 0.6

    return {
        "folds": folds,
        "positive_folds": positive_folds,
        "total_folds": n_folds,
        "consistent": consistent,
    }


def multiple_testing_correction(p_values: list, method: str = "holm") -> list:
    """
    Correct p-values for multiple testing (data snooping prevention).
    Methods: 'holm' (Holm-Bonferroni), 'bonferroni', 'bh' (Benjamini-Hochberg)

    Returns: list of corrected p-values
    """
    p = np.array(p_values, dtype=float)
    n = len(p)

    if n == 0:
        return []

    if method == "bonferroni":
        corrected = np.minimum(p * n, 1.0)

    elif method == "holm":
        sorted_idx = np.argsort(p)
        corrected = np.zeros(n)
        for rank, idx in enumerate(sorted_idx):
            corrected[idx] = min(p[idx] * (n - rank), 1.0)
        # Enforce monotonicity
        for i in range(1, n):
            idx = sorted_idx[i]
            prev_idx = sorted_idx[i - 1]
            corrected[idx] = max(corrected[idx], corrected[prev_idx])

    elif method == "bh":
        sorted_idx = np.argsort(p)
        corrected = np.zeros(n)
        for rank, idx in enumerate(sorted_idx):
            corrected[idx] = min(p[idx] * n / (rank + 1), 1.0)
        # Enforce monotonicity (reverse)
        for i in range(n - 2, -1, -1):
            idx = sorted_idx[i]
            next_idx = sorted_idx[i + 1]
            corrected[idx] = min(corrected[idx], corrected[next_idx])

    else:
        raise ValueError(f"Unknown method: {method}. Use 'holm', 'bonferroni', or 'bh'.")

    return corrected.tolist()


def economic_significance(
    mean_daily_return: float,
    transaction_cost: float = 0.0005,
    trades_per_year: int = 252,
    holding_days: float = 1.0,
) -> dict:
    """
    Check whether a strategy edge survives transaction costs.

    mean_daily_return: average daily return of the strategy
    transaction_cost: round-trip cost per trade (default 0.05% = 5 bps)
    trades_per_year: how often the strategy trades
    holding_days: average holding period

    Returns: gross_annual, cost_annual, net_annual, survives
    """
    trades_per_year_actual = trades_per_year / holding_days
    gross_annual = mean_daily_return * 252
    cost_annual = transaction_cost * trades_per_year_actual
    net_annual = gross_annual - cost_annual

    return {
        "gross_annual_return": float(gross_annual),
        "cost_annual": float(cost_annual),
        "net_annual_return": float(net_annual),
        "trades_per_year": float(trades_per_year_actual),
        "survives_costs": net_annual > 0,
    }


def full_skeptic_report(
    signal: pd.Series,
    returns: pd.Series,
    strategy_name: str = "unnamed",
    transaction_cost: float = 0.0005,
) -> dict:
    """
    Run the complete Skeptic battery on a strategy signal.
    Returns a comprehensive report with pass/fail for each test.
    """
    # Strategy returns
    aligned = pd.DataFrame({"signal": signal, "ret": returns}).dropna()
    aligned = aligned[aligned["signal"] != 0]
    strategy_returns = aligned["signal"] * aligned["ret"]

    # Run all tests
    t = t_test_returns(strategy_returns)
    b = bootstrap_confidence_interval(strategy_returns)
    p = permutation_test(signal, returns)
    w = walk_forward_test(signal, returns)
    e = economic_significance(
        strategy_returns.mean() if len(strategy_returns) > 0 else 0,
        transaction_cost=transaction_cost,
    )

    # Overall verdict
    tests_passed = sum([
        t.get("significant", False),
        not b.get("zero_in_ci", True),
        p.get("significant", False),
        w.get("consistent", False),
        e.get("survives_costs", False),
    ])

    return {
        "strategy": strategy_name,
        "n_observations": len(aligned),
        "t_test": t,
        "bootstrap": b,
        "permutation": p,
        "walk_forward": w,
        "economic_significance": e,
        "tests_passed": tests_passed,
        "tests_total": 5,
        "verdict": "PASS" if tests_passed >= 4 else "WEAK" if tests_passed >= 3 else "FAIL",
    }


if __name__ == "__main__":
    # Demo with random data
    np.random.seed(42)
    n = 500
    fake_signal = pd.Series(np.random.choice([-1, 0, 1], size=n, p=[0.3, 0.4, 0.3]))
    fake_returns = pd.Series(np.random.normal(0.0005, 0.02, size=n))

    print("=== Statistics Engine Demo (random data — should mostly FAIL) ===\n")

    report = full_skeptic_report(fake_signal, fake_returns, "random_demo")

    print(f"Strategy: {report['strategy']}")
    print(f"Observations: {report['n_observations']}")
    print(f"\nt-test:       p={report['t_test']['p_value']:.4f}  {'PASS' if report['t_test']['significant'] else 'FAIL'}")
    print(f"Bootstrap:    CI [{report['bootstrap']['ci_lower']:.6f}, {report['bootstrap']['ci_upper']:.6f}]  {'PASS' if not report['bootstrap']['zero_in_ci'] else 'FAIL'}")
    print(f"Permutation:  p={report['permutation']['p_value']:.4f}  {'PASS' if report['permutation']['significant'] else 'FAIL'}")
    print(f"Walk-forward: {report['walk_forward']['positive_folds']}/{report['walk_forward']['total_folds']} positive  {'PASS' if report['walk_forward']['consistent'] else 'FAIL'}")
    print(f"Econ signif:  net={report['economic_significance']['net_annual_return']:.4f}  {'PASS' if report['economic_significance']['survives_costs'] else 'FAIL'}")
    print(f"\nVerdict: {report['verdict']} ({report['tests_passed']}/{report['tests_total']} tests passed)")
