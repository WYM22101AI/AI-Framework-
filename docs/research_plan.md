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

## Technology Stack

### Two AI Systems (don't conflate them)

| System | Role | What it is |
|--------|------|-----------|
| **CoCo Desktop** | Software engineer | Builds, debugs, maintains the codebase |
| **smolagents (HuggingFace)** | Research team | Runs the 6-agent quant research loop |

CoCo develops the platform. smolagents runs the research.

### Full Stack

```
Development:          GitHub + CoCo Desktop
Agent orchestration:  HuggingFace smolagents (multi-agent, MCP, tool-calling)
Models:               HF models / Ollama (local) / OpenAI/Anthropic (when needed)
Financial infra:      Alpaca (prices, trading, Skills library)
Data:                 FRED, SEC, Alpha Vantage, Alpaca, DuckDB
Statistics:           SciPy, statsmodels, scikit-learn, NumPy
Backtesting:          Our engine + Alpaca Skills methodology
Execution:            Alpaca paper trading API
```

### Why smolagents?

HuggingFace's `smolagents` is an open-source agent framework that supports:
- Multi-step agents that write/execute Python
- Tool calling and MCP integration
- Multiple model backends (HF, Ollama, OpenAI, Anthropic)
- Multi-agent orchestration (managed agents)
- HF Spaces as importable tools

Reference: https://huggingface.co/docs/smolagents/main/index
Agents course: https://huggingface.co/learn/agents-course/unit0/introduction

**Caveat:** smolagents is marked as experimental. Our core research logic (features, stats, backtests, DuckDB schema) must remain ordinary Python we own. smolagents is an orchestration layer we can replace if needed.

---

## Build vs Borrow: What We Own, What We Reference

### BORROW: Standard implementations (don't reinvent)

Use established libraries/projects for industry-standard calculations:

| What | Source | Why borrow |
|------|--------|-----------|
| Yield / return calculations | numpy, pandas | Standard financial math |
| Event study methodology | statsmodels, reference projects | Well-established academic method |
| Backtesting framework | Alpaca Skills + our engine | Standardized guardrails |
| Execution/order mechanics | Alpaca Skills | Boring but critical correctness |
| Agent orchestration | smolagents | Don't build our own agent framework |
| Financial NER / sentiment | HuggingFace models/Spaces | Pretrained is better than DIY |
| Statistical tests | SciPy, statsmodels | Bootstrap, permutation, t-tests |
| Technical indicators | pandas-ta or manual (already done) | Standard formulas |

### BUILD: Our custom research layer (this is our edge)

| What | Why custom |
|------|-----------|
| Feature selection + validation | Our research methodology |
| Skeptic kill criteria | Our quality thresholds |
| Hypothesis generation (Scout) | Our market intuition + AI |
| Regime classification | Our definition of market states |
| Research memory schema | Our experiment tracking |
| Strategy filtering (Gatekeeper) | Our promotion criteria |
| Governor research agenda | Our research priorities |
| Noise filtering philosophy | Our core differentiator |

### STUDY: Open-source reference projects (mine for architecture, not strategy)

| Project | Stars | What to study |
|---------|-------|--------------|
| TradingAgents (TauricResearch) | 15K+ | Multi-agent architecture, structured outputs, decision logs |
| quant-agent (yebof) | — | 9 specialized agents, deterministic risk filters, quarterly meta-reflector |
| Alpha-Agent (henrygers) | — | Alpha discovery cycle, evolving knowledge base |
| Magents (LLMQuant) | — | Multi-strategy simulation, transaction costs, slippage modeling |
| FinResearch-Agent (Caspian-Lin) | — | Research memo generation, "if backtest looks too good, suspect a bug" |
| QuantDinger (dorucioclea) | — | Research-to-execution boundary, audit logs |

**How to use these:** Ask CoCo to analyze their architecture, agent roles, evaluation methods, data schemas, and statistical safeguards. Do NOT copy trading strategies. Borrow engineering patterns.

---

## Reference Governance: How We Leverage External Knowledge

### Levels of leveraging (from lightest to heaviest)

| Level | What | Goes in our repo? | Example |
|-------|------|-------------------|---------|
| **Study** | Read architecture/design ideas | No (record notes in `docs/references/`) | TradingAgents agent separation pattern |
| **Adapt** | Take a prompt/workflow idea, rewrite it | Yes (our own code) | Agent role definitions inspired by quant-agent |
| **Install** | Use as a pip dependency | No (declared in requirements.txt) | smolagents, scipy, pandas |
| **Download** | Cache a model locally | No (lives in ~/.cache or model dir) | HF financial sentiment model |
| **Vendor** | Copy a specific component (with license) | Yes (with provenance) | A transaction-cost module |
| **Clone wholesale** | Copy an entire project | **NEVER** | |

### What lives WHERE

**In our Git repository (we own this):**
```
agents/          Our agent definitions (Scout, Skeptic, etc.)
scripts/         Our feature engine, stats, backtester
research/        Our methodology rules, experiment protocols
docs/references/ Notes on what we studied and borrowed
```

**In requirements.txt (installed, not committed):**
```
smolagents, scipy, statsmodels, pandas, alpaca-trade-api, fredapi
```

**In local cache (not in Git, not in repo):**
```
~/.cache/huggingface/    Downloaded HF models
```

**NOT in our repo:**
```
Cloned copies of TradingAgents, quant-agent, etc.
Other people's complete projects
```

### Reference documentation format

For each external resource we study, create a file in `docs/references/`:

```markdown
# [Project Name]

Source: [URL]
Commit/version reviewed: [SHA or version]
Date reviewed: [date]
License: [MIT/Apache/etc.]

## What we learned
- ...

## What we borrowed (if anything)
- ...

## Our implementation
- ...
```

This gives us a **research bibliography for software architecture** — we know exactly where ideas came from and can reproduce the environment.

### Pin everything

For reproducibility, always record:
- GitHub repos: commit SHA + date
- HF models: model name + revision
- Alpaca Skills: commit/version
- Python packages: pinned versions in requirements.txt

If a backtest says "this strategy works," we need to reproduce the exact environment that produced that result.

---

## Target Project Structure

Where we're heading (not all at once — grows over the 6-month timeline):

```
family-quant-ai/
|
|-- config.py                    # Central settings
|-- update_market_data.py        # Daily data pipeline orchestrator
|-- requirements.txt             # Pinned dependencies
|-- .env / .env.example          # API keys (gitignored / template)
|
|-- scripts/                     # Data fetchers + engines (Phase 1-2)
|   |-- market_fetcher.py
|   |-- fred_fetcher.py
|   |-- earnings_fetcher.py
|   |-- sec_fetcher.py
|   |-- options_fetcher.py
|   |-- news_fetcher.py
|   |-- storage.py
|   |-- feature_engine.py
|   |-- stats_engine.py          # Statistical tests (Phase 3)
|   |-- backtester.py            # Backtest engine (Phase 4)
|   |-- signal_generator.py      # Strategy signals (Phase 5)
|   |-- skeptic.py               # Kill bad ideas (Phase 6)
|   |-- strategy_filter.py       # Gatekeeper (Phase 6)
|   +-- paper_trader.py          # Alpaca paper execution (Phase 7)
|
|-- agents/                      # AI agent definitions (Phase 7-8)
|   |-- scout.py                 # Anomaly detection
|   |-- context.py               # Regime classification
|   |-- feature_miner.py         # Propose new features
|   |-- skeptic_agent.py         # Orchestrates stats_engine
|   |-- experimenter.py          # Designs and runs experiments
|   |-- gatekeeper.py            # Promotion decisions
|   +-- governor.py              # Research agenda
|
|-- research/                    # Our methodology (our IP)
|   |-- methodology.md           # Validation rules
|   |-- experiment_protocol.md   # How we run experiments
|   +-- anti_leakage_rules.md    # Preventing look-ahead bias
|
|-- data/                        # Local DuckDB + generated data (gitignored)
|   +-- market_data.duckdb
|
|-- notebooks/                   # Interactive exploration
|   +-- exploration.ipynb
|
|-- docs/                        # Documentation
|   |-- research_plan.md         # This document
|   |-- timeline.md              # Project timeline
|   |-- project_log.md           # Session history
|   |-- learning_roadmap.md      # Educational resources
|   +-- references/              # External knowledge bibliography
|       |-- tradingagents.md
|       |-- quant-agent.md
|       |-- alpha-agent.md
|       |-- magents.md
|       |-- finresearch-agent.md
|       |-- alpaca-skills.md
|       +-- huggingface-smolagents.md
|
|-- skills/                      # Adopted skill definitions (Phase 7)
|   |-- alpaca/                  # From Alpaca Skills repo (pinned version)
|   +-- research/                # Our own research methodology skill
|
+-- archive/                     # Old experimental scripts
```

### What's OURS vs what's BORROWED

```
OURS (our edge, our IP):
  agents/*           - How we define research agents
  research/*         - Our validation methodology
  scripts/skeptic.py - Our kill criteria
  scripts/feature_engine.py - Our feature definitions
  data/              - Our accumulated research results
  skills/research/   - Our research methodology skill

BORROWED (standard, don't reinvent):
  requirements.txt deps  - smolagents, scipy, pandas, etc.
  skills/alpaca/         - Alpaca's proven trading mechanics
  scripts/stats_engine.py - Built on scipy/statsmodels (standard tests)
  Return/yield formulas  - numpy (industry standard math)
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
| 3 | Build backtester.py (using Alpaca Skills methodology) | Can test hypotheses |
| 4 | Implement Strategy A (momentum) | Simplest to test |
| 5 | Run full Skeptic pipeline on Strategy A | Validate the framework |
| 6 | Add Strategies B-E | Expand hypothesis pool |
| 7 | Build Gatekeeper logic | Filter survivors |
| 8 | Connect paper trading (using Alpaca Skills for execution) | Go live |
| 9 | Add Governor + research memory | Self-improvement |
| 10 | Evaluate Unusual Whales / Massive data (only if research needs it) | Expand information |

---

## Three-Layer Architecture

### Layer A: Ground Truth Mechanics (DON'T reinvent)

Use Alpaca Skills Library (https://github.com/alpacahq/alpaca-skills) for:

| Skill | What it standardizes |
|-------|---------------------|
| `alpaca-trading-backtest` | Backtesting methodology, guardrails, assumptions, reporting |
| `alpaca-broker-market-data` | Data acquisition patterns, API conventions |
| `alpaca-broker-trading-orders` | Order semantics, types, execution |
| `alpaca-broker-reconciliation-idempotency` | Prevent duplicate orders on retries |
| `alpaca-broker-rate-limits-resilience` | API throttling, transient failure handling |
| `alpaca-broker-money-precision` | Financial calculation precision (not naive floats) |

### Layer B: Research Assumptions (WE define explicitly)

These are choices, not facts:

```
Decision time:        6:00 PM ET (after close)
Execution:            Next market open
Fill price:           Open price + estimated slippage
Slippage model:       0.05% of trade value (based on historical spread)
Position sizing:      Volatility-adjusted (lower vol = larger position)
Max position:         25% of portfolio
Universe:             50-100 liquid US stocks
Rebalance:            Daily
Holding period:       Variable (1-20 days based on strategy)
Commission:           $0 (Alpaca)
Market impact:        Estimated from relative volume
Information cutoff:   Only data available before decision timestamp
```

### Layer C: Our Secret Sauce (WHERE we spend intellectual effort)

```
What information matters?
        |
What is noise?
        |
What combinations matter?
        |
Under what market regimes?
        |
How stable is the relationship?
        |
Can it survive out-of-sample?
        |
Can it survive realistic execution?
```

The differentiator: **AI finds hypotheses, deterministic science tries to destroy them, only robust signals survive.**

---

## Data Source Roadmap

### Now (free, already integrated)

| Source | Data | Status |
|--------|------|--------|
| Alpaca | Stock prices, news, paper trading | WORKING |
| FRED/ALFRED | Macro indicators with release dates | WORKING |
| Alpha Vantage | Earnings calendar, EPS surprises | WORKING |
| SEC EDGAR | Revenue, income, filings with timestamps | WORKING |

### Experiment Next (when research identifies a specific need)

| Source | Data | When to add |
|--------|------|-------------|
| Unusual Whales | Options flow, GEX, dark pool, MCP+Skills | When we test "does options positioning add information?" |
| Massive (Polygon) | Deep historical trades/quotes, options, MCP | When we need execution realism or longer history |
| Prediction markets | Event probabilities (Fed, elections) | When we test macro-event strategies |

### Later (only if proven valuable)

| Source | Data | When |
|--------|------|------|
| Databento | Tick data, order book, microstructure | If execution dynamics explain strategy behavior |
| Nasdaq Data Link | Specialized alternative datasets | If specific alternative data hypothesis emerges |

### Rule: Every new data source must prove its value

```
BASE MODEL (existing features)
    |
+ new data source
    |
Does out-of-sample performance improve?
    |
Does it add information BEYOND existing features?
    |
Does it survive transaction costs?
    |
Does it improve across regimes?
    |
YES to all? --> Keep it
NO? --> Drop it, record the lesson
```

---

## Execution Realism Module

Don't assume: `signal -> close price -> magically filled`

Instead model:
```
Signal generated at 5:30 PM
        |
Eligible for execution: next open
        |
Historical bid/ask spread at open
        |
Estimated slippage (f(volume, trade size))
        |
Simulated fill price
        |
Actual position
```

Key warning from Alpaca's own disclosure: backtest calculations may not account for liquidity constraints, sudden price moves, execution delays, and order priority.

Our backtest should explicitly test sensitivity to:
- 2x assumed spread
- Execution at open vs VWAP vs close
- Removing best 5 trades (were they luck?)
- Different market hours assumptions

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
9. **Don't let data access become feature soup.** 500 features that maximize historical Sharpe = overfitting.
10. **Every data source must earn its place.** Prove it adds incremental out-of-sample value.
