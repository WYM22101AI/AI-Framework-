# Research Development Plan: Family Quant AI

## Vision

Build a self-improving quantitative research system where:
- **AI agents generate hypotheses** (what looks unusual, what might be an edge)
- **Deterministic code tests truth** (statistics, backtests, significance tests)
- **Only robust signals survive** to paper trading
- **Research memory prevents repeating failures**

The core philosophy: **Our edge is not "AI finds patterns." Our edge is: AI finds hypotheses, deterministic science tries to destroy them, only robust signals survive.**

---

## System Architecture: 6 Agents + 2 Engines

```
                         +------------------------+
                         |   RESEARCH GOVERNOR    |
                         |   (Chief Scientist)    |
                         +-----------+------------+
                                     |
              +----------------------+----------------------+
              |                      |                      |
              v                      v                      v
        +-----------+          +----------+          +-----------+
        |   SCOUT   |          | CONTEXT  |          |  FEATURE  |
        | anomalies |          | / REGIME |          |   MINER   |
        +-----+-----+          +-----+----+          +-----+-----+
              |                      |                      |
              +----------------------+----------------------+
                                     v
                            +----------------+
                            |    SKEPTIC     |
                            |  (Validator)   |
                            +-------+--------+
                                    |
                              surviving ideas
                                    v
                            +----------------+
                            |  EXPERIMENTER  |
                            |  (Backtester)  |
                            +-------+--------+
                                    |
                                    v
                            +----------------+
                            |  GATEKEEPER    |
                            | (Paper Gate)   |
                            +-------+--------+
                                    |
                             feedback / results
                                    |
                                    +-------> Governor
```

### What Each Agent Does

| Agent | Role | LLM or Code? |
|-------|------|--------------|
| **Governor** | Decides what to investigate next, manages research agenda | LLM |
| **Scout** | Finds anomalies (unusual volume, price divergences, option activity) | LLM + simple stats |
| **Context/Regime** | Determines market environment (trending, volatile, risk-on/off) | Code (rules + clustering) |
| **Feature Miner** | Proposes new features/factors to test | LLM |
| **Skeptic** | Tries to KILL ideas with statistical rigor | **Strictly code** |
| **Experimenter** | Runs formal backtests with proper methodology | **Strictly code** |
| **Gatekeeper** | Decides if a strategy deserves paper trading capital | Code + LLM review |

### Critical Design Rules

1. **LLMs never compute statistics.** They request tests; Python executes them.
2. **Agents cannot directly modify strategies.** They submit hypotheses; the experimental machinery judges.
3. **The Skeptic's job is to kill ideas.** If it can't kill one, that's interesting.
4. **Research memory is structured** (a database), not conversation history.

### Underlying Engines (NOT agents — deterministic code)

```
        DATA LAYER
            |
       DuckDB + APIs
            |
     +------+-------+
     |              |
 STATISTICS      BACKTEST
 ENGINE          ENGINE
     |              |
     +------+-------+
            |
       PAPER TRADING
          Alpaca
```

---

## Phase Overview

```
Phase 1: DATA FOUNDATION              [COMPLETE]
Phase 2: FEATURE ENGINEERING           [WORKING - feature_engine.py tested]
Phase 3: STATISTICS ENGINE             
Phase 4: BACKTESTING ENGINE            
Phase 5: SIGNAL GENERATION (Scout)     
Phase 6: SKEPTIC + GATEKEEPER          
Phase 7: PAPER TRADING                 
Phase 8: RESEARCH GOVERNOR + MEMORY    
```

---

## Phase 1: Data Foundation [COMPLETE]

Pipeline fetches from 5+ sources daily:

| Source | Data | Rows |
|--------|------|------|
| Alpaca | Daily OHLCV (TSLA, AAPL, NVDA, SPY) | 6,113 |
| FRED | Macro indicators (CPI, rates, GDP, VIX, etc.) | 29,572 |
| Alpha Vantage | Quarterly earnings with surprises | 296 |
| SEC EDGAR | Revenue, income, assets from filings | 214 |
| Alpaca | News headlines | 55 |

---

## Phase 2: Feature Engineering [WORKING]

**Status:** `scripts/feature_engine.py` generates 3,987 rows with 11 features.

### Technical Features (per stock)
- Returns: 1d, 5d, 20d, 60d
- Volatility: 20d annualized
- Moving average distance: MA50, MA200
- RSI (14-day)
- Bollinger Band position
- Relative volume (vs 20d avg)
- Relative strength vs SPY

### Still to add:
- Regime features (VIX level, yield curve, Fed direction)
- Fundamental features (days since earnings, EPS surprise)
- Event features (earnings within 7 days)
- Store computed features in DuckDB `daily_features` table

---

## Phase 3: Statistics Engine

**Goal:** A reusable library of statistical tests that the Skeptic calls.

### Tests to implement:

```python
# scripts/stats_engine.py

def t_test(returns: Series) -> float:
    """Is mean return != 0? Returns p-value."""

def bootstrap_test(returns: Series, n_samples=10000) -> dict:
    """Bootstrap confidence interval for mean return."""

def permutation_test(signal: Series, returns: Series, n_perms=5000) -> float:
    """Shuffle signal, recompute metric. What % beat the real metric?"""

def walk_forward_test(signal, returns, n_folds=5) -> dict:
    """Rolling out-of-sample test. Returns per-fold Sharpe."""

def multiple_testing_correction(p_values: list, method='holm') -> list:
    """Correct for data snooping when testing many hypotheses."""

def economic_significance(mean_return, transaction_cost=0.0005) -> bool:
    """Is the edge large enough to survive costs?"""
```

### Key Principle

"Statistically significant" is necessary but NOT sufficient.
Must also be **economically meaningful** (survives transaction costs).

---

## Phase 4: Backtesting Engine

**Goal:** Rigorous, no-look-ahead backtesting with proper methodology.

### Design Rules
1. **Entry at next day's open** (not today's close — that's look-ahead)
2. **Include costs:** 0.05% spread per trade
3. **Walk-forward:** Train on 2016-2022, validate 2023-2024, holdout 2025-2026
4. **Report honestly:** Sharpe, drawdown, hit rate, p-value, turnover

### Metrics
- Annualized return (365 calendar days)
- Sharpe ratio
- Max drawdown
- Win rate
- Average win / average loss ratio
- Turnover (trades per year)
- p-value (t-test on daily returns)
- Comparison vs SPY buy-and-hold

### Overfitting Detection
- In-sample Sharpe > 2x out-of-sample Sharpe → likely overfit
- Monte Carlo: randomize entry dates, what % beat real?
- Parameter sensitivity: does small parameter change destroy the edge?

---

## Phase 5: Signal Generation (The Scout)

**Goal:** Generate "trading opportunity" hypotheses.

The Scout scans daily data and flags anomalies:

### Strategy Hypotheses to Test

**A. Momentum**
- 20d return > 0 AND price > MA50 → bullish
- Regime-conditional: only in trending markets

**B. Mean Reversion**
- RSI < 30 AND below lower Bollinger → oversold bounce
- Regime-conditional: only in range-bound/low-vol markets

**C. Earnings Drift (Post-Earnings Momentum)**
- EPS surprise > 5% within 20 days → bullish drift
- EPS surprise < -5% → bearish drift

**D. Unusual Activity**
- Volume > 3x normal without corresponding news → investigate
- Options put/call ratio spike → possible informed trading

**E. Macro Regime Switch**
- VIX crosses from low to high → reduce exposure
- Yield curve uninverts → historical bullish signal

### Output Format
Each hypothesis becomes a structured record:
```
hypothesis_id: uuid
created_at: timestamp
origin: "scout"
description: "TSLA: volume 4.2x normal, no earnings within 7 days, no major news"
features_used: ["relative_volume", "days_since_earnings", "news_count"]
proposed_direction: "long"
confidence: 0.65
regime: "LOW_VOLATILITY"
status: "pending_skeptic"
```

---

## Phase 6: Skeptic + Gatekeeper

### The Skeptic's Kill Criteria

A hypothesis DIES if ANY of these hold:
1. p-value > 0.05 after multiple-testing correction
2. Effect disappears in permutation test
3. Only works in one time period (walk-forward fails)
4. Only works for one stock (not cross-sectional)
5. Edge < transaction costs (not economically meaningful)
6. Driven by a known confound (e.g., earnings proximity explains it away)

### The Gatekeeper's Promotion Criteria

A surviving strategy gets paper-traded ONLY if ALL hold:
1. Out-of-sample Sharpe > 0.5
2. Max drawdown < 30%
3. Works in at least 2 stocks
4. Stable across 2+ time periods
5. Beats SPY buy-and-hold after costs
6. Does NOT massively degrade current portfolio (if combined)

---

## Phase 7: Paper Trading

### Daily Workflow (automated)

```
5:00 PM  Market closes
5:15 PM  update_market_data.py runs (all sources)
5:20 PM  feature_engine.py runs (compute features)
5:25 PM  signal_generator.py runs (Scout checks for anomalies)
5:30 PM  paper_trader.py runs:
         - Check surviving strategies
         - Compute target positions
         - Place orders via Alpaca paper trading API
         - Log decisions with reasoning
6:00 PM  Research Governor reviews results
```

### Position Sizing
- Max 25% per position
- Size proportional to signal confidence
- Reduce size in HIGH_VOLATILITY regime

---

## Phase 8: Research Governor + Memory

### Research Memory Database

```sql
CREATE TABLE research_hypotheses (
    hypothesis_id TEXT PRIMARY KEY,
    created_at TIMESTAMP,
    origin TEXT,          -- 'scout', 'governor', 'feature_miner'
    description TEXT,
    features_used TEXT,   -- JSON array
    regime TEXT,
    status TEXT           -- 'pending', 'testing', 'rejected', 'accepted', 'deployed'
);

CREATE TABLE experiments (
    experiment_id TEXT PRIMARY KEY,
    hypothesis_id TEXT,
    dataset_version TEXT,
    parameters TEXT,      -- JSON
    methodology TEXT,
    train_period TEXT,
    test_period TEXT
);

CREATE TABLE experiment_results (
    experiment_id TEXT PRIMARY KEY,
    sharpe DOUBLE,
    annualized_return DOUBLE,
    max_drawdown DOUBLE,
    p_value DOUBLE,
    effect_size DOUBLE,
    turnover DOUBLE,
    survives_permutation BOOLEAN,
    survives_walk_forward BOOLEAN
);

CREATE TABLE lessons_learned (
    lesson_id TEXT PRIMARY KEY,
    hypothesis_id TEXT,
    result TEXT,          -- 'rejected', 'accepted'
    why TEXT,             -- explanation
    what_to_try_next TEXT
);
```

### What the Governor Does Weekly
1. Reviews all experiments from the past week
2. Identifies patterns in failures ("all momentum strategies failed this month — regime changed?")
3. Proposes 1-3 new hypotheses to test
4. Decides whether to pause/resume deployed strategies based on regime

---

## Implementation Priority

| Step | What | Why first |
|------|------|-----------|
| 1 | Store features in DuckDB | Enables everything downstream |
| 2 | Build stats_engine.py | The Skeptic needs tools |
| 3 | Build backtester.py | Can test hypotheses |
| 4 | Implement Strategy A (momentum) | Simplest to test |
| 5 | Run full Skeptic pipeline on Strategy A | Validate the framework |
| 6 | Add Strategies B-E | Expand hypothesis pool |
| 7 | Build Gatekeeper logic | Filter survivors |
| 8 | Connect paper trading | Go live |
| 9 | Add Governor + research memory | Self-improvement |

---

## Principles

1. **Simple beats complex.** A 3-feature model that works > 100-feature model that's overfit.
2. **Out-of-sample or it doesn't count.** Never evaluate on training data.
3. **The null hypothesis is: this doesn't work.** Prove it wrong with data.
4. **Markets change.** A strategy from 2020 may not work in 2026.
5. **Transaction costs matter.** 0.1% daily edge can lose to spreads.
6. **Probability, not prediction.** We want 55% win rates, not certainty.
7. **LLMs reason, code calculates.** Never let AI compute a p-value.
8. **The Skeptic is your best friend.** Ideas that survive it are rare and valuable.
