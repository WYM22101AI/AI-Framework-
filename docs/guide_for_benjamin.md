# Family Quant AI: Technical Guide for Benjamin

**Written by: Dad + CoCo (AI coding assistant)**  
**Last updated: September 2026 (Phase 8 Complete — 90% Milestone)**

Hey Benjamin — this document explains everything we've built, how the whole system works, the math and AI behind it, and why we made each engineering decision. Read it start to finish, then keep it as your reference handbook.

---

## What We're Building

We're building an autonomous, AI-assisted quantitative research platform for financial markets:
1. **Multi-Source Data Ingestion**: Downloads market data every day (stock prices, economic releases, earnings, SEC filings, options flow, and news).
2. **Feature Engineering**: Calculates 24 quantitative metrics per stock per day describing price action, volatility, market regimes, and algo herding.
3. **Hypothesis Generation**: Formulates structured trading ideas based on anomalies and market conditions.
4. **The Skeptic (Statistical Engine)**: Rigorously stress-tests every hypothesis with math (bootstrap resampling, permutation shuffles, walk-forward validation) to kill bad ideas.
5. **AI Research Agents**: Autonomous agents (Scout, Regime, Governor, Experimenter, Skeptic, Gatekeeper) that collaborate to discover, test, and promote strategies.
6. **Paper Trading**: Executes approved survivor strategies in real-time via Alpaca's paper trading API.
7. **Automated Daily Research**: Runs unattended at 5:30 PM daily after market close, wakes the computer if asleep, checks market holidays, and generates executive reports.

Think of it as a **computational science lab for markets**. We don't guess — we run reproducible experiments.

---

## The Big Idea: The "Skeptic" Philosophy

Most people who try to trade with AI make this mistake:

```
"AI, should I buy TSLA?" --> LLM says "Yes!" --> They buy --> Lose money
```

LLMs are pattern matchers and will hallucinate confidence on pure noise.

**What WE do instead (The Three-Layer Architecture):**

```
 ┌────────────────────────────────────────────────────────┐
 │ 1. Ground Truth Mechanics (Strict Python / DuckDB)      │
 │    Data ingestion, accounting, trade execution, math   │
 └──────────────────────────┬─────────────────────────────┘
                            │
 ┌──────────────────────────▼─────────────────────────────┐
 │ 2. Research & Hypothesis (AI Agents + Exploration)     │
 │    Scout finds anomalies, Governor proposes ideas      │
 └──────────────────────────┬─────────────────────────────┘
                            │
 ┌──────────────────────────▼─────────────────────────────┐
 │ 3. The Skeptic & Gatekeeper (Statistical Destruction)  │
 │    5 math tests try to PROVE IT DOESN'T WORK.          │
 │    Only strategies that CANNOT BE KILLED get traded.   │
 └────────────────────────────────────────────────────────┘
```

> **The Golden Rule**: AI agents NEVER compute statistics or make trade decisions directly. AI proposes hypotheses; deterministic Python math attempts to destroy them. Only the survivors get funded.

---

## The 6-Agent AI Architecture (Phase 8)

We built an ensemble of specialized research agents in the `agents/` directory:

```
                      ┌────────────────────────┐
                      │     GOVERNOR AGENT     │
                      │  (Weekly Research Plan)│
                      └───────────┬────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
         ▼                        ▼                        ▼
 ┌───────────────┐        ┌───────────────┐        ┌───────────────┐
 │  SCOUT AGENT  │        │ REGIME AGENT  │        │ EXPERIMENTER  │
 │(Anomaly Scan) │        │ (Market State)│        │  (Backtester) │
 └───────┬───────┘        └───────┬───────┘        └───────┬───────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                                  ▼
                      ┌────────────────────────┐
                      │     SKEPTIC AGENT      │
                      │   (5-Gate Kill Switch) │
                      └───────────┬────────────┘
                                  │ (If Passed)
                                  ▼
                      ┌────────────────────────┐
                      │    GATEKEEPER AGENT    │
                      │  (Portfolio Promotion) │
                      └───────────┬────────────┘
                                  │
                                  ▼
                         Alpaca Paper Trading
```

| Agent | File | What it Does | Method |
|---|---|---|---|
| **Regime** | `agents/regime.py` | Classifies macro climate: `LOW_VOL`, `RISK_ON`, `RISK_OFF`, `HIGH_VOL` | VIX + SPY vs MA50 |
| **Scout** | `agents/scout.py` | Scans daily features across all stocks to find unusual volume, RSI extremes, large moves | Statistical Anomaly Scanner |
| **Governor** | `agents/governor.py` | Reviews weekly experiments, identifies dead strategy families, proposes new research | Research Manager |
| **Experimenter** | `agents/experimenter.py` | Takes a hypothesis, generates signals, runs out-of-sample backtest, logs to DuckDB | Deterministic Backtesting |
| **Skeptic** | `agents/skeptic.py` | 5-gate evaluation: Sharpe $\ge 0.5$, Drawdown $< 30\%$, Trades $\ge 30$, Beats SPY, No Overfitting | Statistical Battery |
| **Gatekeeper** | `agents/gatekeeper.py` | Portfolio risk check: prevents single-stock concentration and manages position sizing | Portfolio Manager |
| **Orchestrator**| `agents/research_loop.py` | Chained daily loop: Data $\rightarrow$ Features $\rightarrow$ Regime $\rightarrow$ Scout $\rightarrow$ Paper Trade | Command Center |

---

## The 24 Daily Features

Every day, `scripts/feature_engine.py` computes 24 numbers for each stock:

### 1. Price & Momentum Features
- `return_1d`, `return_5d`, `return_20d`, `return_60d`: Returns over 1, 5, 20, and 60 days.
- `volatility_20d`: Realized 20-day annualized volatility.
- `distance_from_ma50`, `distance_from_ma200`: Percentage distance from moving averages.
- `relative_strength_vs_spy`: Stock performance minus SPY performance over 20 days.

### 2. Oscillator & Volume Features
- `rsi_14`: Relative Strength Index (0–100). Below 30 = oversold, above 70 = overbought.
- `relative_volume`: Today's volume divided by the 20-day average volume.
- `bollinger_position`: Normalized position within Bollinger Bands ($-1.0$ to $+1.0$).

### 3. AI Cascade & Herding Features (New!)
*Built to detect when algorithmic trading models create feedback loops and amplify moves:*
- `volume_acceleration`: Rate of volume increase day-over-day (is the herd piling in?).
- `rsi_velocity`: 3-day rate of change in RSI (sentiment shift speed).
- `move_vs_vol_ratio`: Daily return divided by 20-day daily volatility (abnormality ratio).
- `consecutive_direction_days`: Number of consecutive up or down days (herding persistence).
- `cascade_score`: Multi-factor composite z-score combining volume acceleration, move ratio, and RSI velocity.

### 4. Macro Regime Features
- `vix`: Market fear index from FRED.
- `vix_change_5d`: 5-day percentage change in VIX.
- `fed_funds`: Current Federal Reserve interest rate.
- `treasury_10y`: 10-Year US Treasury bond yield.

### 5. Fundamental & Event Features
- `days_since_earnings`: Days elapsed since last quarterly earnings release.
- `last_eps_surprise`: Percentage EPS beat or miss vs Wall Street consensus.
- `earnings_within_7d`: Boolean flag indicating if earnings report is within 7 days.

---

## Strategy Scorecard: What Works & What Failed

### The Survivors (Passed Skeptic Testing & Paper Trading)

#### 1. VIX-Conditional Mean Reversion (`strategy_mr_vix_tuned`)
- **Core Logic**: When market fear is elevated (**VIX > 20**) and an individual stock is oversold (**RSI < 35**, **Bollinger < -0.6**), buy the bounce.
- **Why it works**: Fear creates indiscriminate selling. High-beta tech stocks overshoot to the downside, then snap back violently.
- **Results**:
  - **AMZN**: **Sharpe 1.46**, Out-of-Sample Return **+13.4%/yr**, Max Drawdown **-3.6%**, Passed **4/5 Skeptic tests**.
  - **NVDA**: **Sharpe 1.02**, Out-of-Sample Return **+11.8%/yr**, Max Drawdown **-7.2%**, Passed **4/5 Skeptic tests**.
- **Status**: **Approved by Gatekeeper & live in Alpaca paper trading.**

#### 2. Pre-Earnings Straddle Volatility (`scripts/earnings_straddle.py`)
- **Core Logic**: Tech mega-caps consistently experience larger price moves on earnings than the options market prices in.
- **Results**: Analyzed 192 historical earnings events across 8 stocks $\rightarrow$ **+2.74% average return per event**.

---

### The Failures (Killed by the Skeptic)

| Strategy | Logic | Result | Why It Failed |
|---|---|---|---|
| **Simple Momentum** | Buy high, sell low | FAIL (Sharpe -0.68) | Classic signal arbitraged away by Wall Street decades ago |
| **Simple Mean Reversion** | Buy RSI < 30 (no VIX) | FAIL (Sharpe 0.10) | Catching falling knives in calm bear markets |
| **Earnings Drift** | Buy on EPS beat | No signal | 5% surprise threshold was too strict |
| **Cascade Overreaction (Fade)** | Fade large cascade moves | FAIL (Sharpe -0.23) | Daily bars are too coarse to catch intraday reversions |

---

## The Skeptic's 5 Statistical Tests

1. **One-Sample t-test**: Is average return statistically greater than 0 ($p < 0.05$)?
2. **Bootstrap Confidence Interval**: Resample returns 10,000 times. Does the 95% confidence interval stay strictly above zero?
3. **Permutation Test**: Shuffle trade signals randomly 5,000 times. Does the real strategy beat $>95\%$ of random shuffles?
4. **Walk-Forward Validation**: Split the 10-year timeline into 5 sequential periods. Does the strategy make money in at least 3 out of 5 periods?
5. **Economic Significance**: After deducting slippage, commissions, and bid-ask spreads (5 bps round-trip), does real net profit remain?

**Verdict**: 4–5 passes = **PASS** | 3 passes = **WEAK** | 0–2 passes = **FAIL (Killed)**

---

## Database Architecture (`market_data.duckdb`)

All data is stored in a high-performance, embedded DuckDB database file:

| Table | Rows | Data Description | Source |
|---|---|---|---|
| `daily_bars` | 29,164 | 10 years of split/dividend adjusted OHLCV for 19 tickers | Alpaca API |
| `macro_releases` | 29,572 | VIX, 10Y Yield, Fed Funds, CPI, GDP, Unemployment | FRED API |
| `earnings` | 296 | Quarterly EPS, estimates, surprise percentages | Alpha Vantage |
| `fundamentals` | 214 | Balance sheet, cash flow, revenue from 10-K/10-Q filings | SEC EDGAR |
| `news` | 55+ | Financial news articles & sentiment tags | Alpaca News |
| `daily_features` | 24,045 | All 24 technical, cascade, regime, and earnings features | Feature Engine |
| `options_activity` | Active | Daily options volume, call/put volume, put/call ratios | Massive (Polygon) |
| `research_experiments`| 25+ | Full audit log of every strategy, Sharpe, drawdown, and verdict | Experimenter Agent |
| `agent_log` | 20+ | Timestamped log of agent thoughts, decisions, and regime states | BaseAgent |
| `trade_log` | Active | Paper trading orders, execution prices, position sizes | Paper Trader |

---

## Automated Daily Scheduling

The system runs autonomously every day at **5:30 PM ET**:

1. **Windows Task Scheduler** triggers `scripts/run_daily.bat`.
2. `daily_research.py` runs the entire research cycle:
   - **Holiday Engine**: Checks US market holidays algorithmically (New Year, MLK, Presidents, Good Friday, Memorial, Juneteenth, July 4, Labor Day, Thanksgiving, Christmas). If the market was closed, it skips cleanly without wasting API calls.
   - **Data Fetch**: Pulls the day's market close prices and economic data.
   - **Feature Engine**: Computes the 24 daily features.
   - **Agent Loop**: Regime agent classifies market state $\rightarrow$ Scout agent flags anomalies.
   - **Paper Trader**: Submits orders for any active Skeptic-approved signals.
   - **Report Generator**: Saves daily summaries to `data/reports/daily_YYYY-MM-DD.txt` and `.json`.

---

## How to Run the Code

```bash
# 1. Activate Python Environment
cd C:\Users\Yaming\family-quant-ai
venv\Scripts\activate

# 2. Run the Daily Research Loop (Dry Run)
python agents/research_loop.py

# 3. Test a Strategy Through the AI Agents
python agents/research_loop.py --experiment --strategy=mr_vix_tuned

# 4. Run the Weekly Governor Review
python agents/research_loop.py --review

# 5. Execute Paper Trading Orders
python scripts/paper_trader.py --execute

# 6. Check Daily Reports
type data\reports\daily_2026-09-10.txt
```

---

## Hands-On Coding Challenges for Benjamin

### Level 1: Beginner
1. Open Python and connect to DuckDB: Write a SQL query to find the top 5 days when VIX spiked the most.
2. Look at `data/reports/`: Read the latest daily report and see what regime the market is in today.

### Level 2: Intermediate
3. Look at `agents/scout.py`: Add a new anomaly rule (for example, flag any stock whose 5-day volatility jumped by more than 50%).
4. Look at `scripts/signal_generator.py`: Write a new strategy combining `rsi_14 < 30` with `relative_volume > 2.0`.
5. Run your new strategy through `agents/experimenter.py` and see what the Skeptic says!

### Level 3: Advanced
6. Explore `scripts/unusual_options.py`: Use the new `options_activity` data to test if high put/call ratios predict next-week stock drops.
7. Study `agents/governor.py`: Upgrade the Governor agent with an LLM prompt to automatically synthesize weekly trade logs into plain English notes.

---

## The Philosophy of Quant Research

1. **Be humble before data**: 95% of trading ideas fail when tested properly. Finding out an idea doesn't work is just as valuable as finding one that does — it saves you real capital.
2. **Never fool yourself**: Overfitting is the easiest trap. Always test on out-of-sample data the model has never seen before.
3. **Control risk first**: Sharpe ratio and drawdown matter more than raw return. A strategy with +15% return and -5% drawdown is 10x better than one with +30% return and -40% drawdown.
4. **Code is your superpower**: With Python, DuckDB, and statistical engines, you have the same quantitative tooling on your laptop that multi-billion dollar hedge funds used a decade ago.
