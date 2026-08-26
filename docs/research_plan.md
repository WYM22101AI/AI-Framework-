# Research Development Plan: Family Quant AI

## Vision

Build a self-improving quantitative research system that:
1. Collects multi-source data daily (already done)
2. Generates "trading opportunity" hypotheses from data patterns
3. Backtests each hypothesis rigorously
4. Filters out ideas that don't survive statistical scrutiny
5. Runs surviving strategies on paper trading
6. Learns from results and proposes new experiments

---

## Phase Overview

```
Phase 1: DATA FOUNDATION          [COMPLETE]
Phase 2: FEATURE ENGINEERING      
Phase 3: SIGNAL GENERATION        
Phase 4: BACKTESTING ENGINE       
Phase 5: STRATEGY FILTERING       
Phase 6: PAPER TRADING            
Phase 7: AI RESEARCH AGENT        
```

---

## Phase 1: Data Foundation [COMPLETE]

**Status:** Done. Pipeline fetches from 5 sources daily.

| Source | Data | Rows |
|--------|------|------|
| Alpaca | Daily OHLCV (TSLA, AAPL, NVDA, SPY) | 6,113 |
| FRED | Macro indicators (CPI, rates, GDP, VIX) | 29,572 |
| Alpha Vantage | Quarterly earnings with surprises | 296 |
| SEC EDGAR | Revenue, income, assets from filings | 214 |
| Alpaca | News headlines | 55 |

**Remaining:** Fix options fetcher (needs alpaca-py client).

---

## Phase 2: Feature Engineering

**Goal:** Transform raw data into ML-ready features that capture the "state of the world" at any given day.

### 2A. Technical Features (from daily_bars)

Per stock, compute rolling features:
- Returns: 1d, 5d, 20d, 60d
- Volatility: 5d, 20d, 60d (std of daily returns)
- Moving averages: 10, 20, 50, 200 day
- Distance from MAs: (price - MA) / MA
- Volume: relative to 20d average
- RSI (14-day)
- Bollinger Band position
- Relative strength vs SPY

### 2B. Market Regime Features (from daily_bars + macro)

- SPY return (1d, 5d, 20d)
- VIX level and change
- Yield curve: 10Y - 2Y spread (from FRED DGS10 - DGS2)
- Fed funds rate level and direction
- Market breadth proxy: % of tickers above 50-day MA

### 2C. Fundamental Features (from earnings + SEC)

- Days since last earnings
- Last EPS surprise (%)
- Trailing 4-quarter revenue growth
- P/E ratio approximation (price / trailing EPS)

### 2D. Event Features

- Earnings in next 7 days? (binary)
- Earnings in last 3 days? (binary)
- Major macro release today? (from FRED release dates)

### Output

A table `daily_features` with one row per (symbol, date):
```sql
CREATE TABLE daily_features (
    symbol TEXT,
    date DATE,
    -- Technical
    return_1d DOUBLE,
    return_5d DOUBLE,
    return_20d DOUBLE,
    volatility_20d DOUBLE,
    rsi_14 DOUBLE,
    distance_from_ma50 DOUBLE,
    relative_volume DOUBLE,
    relative_strength_vs_spy DOUBLE,
    -- Regime
    spy_return_5d DOUBLE,
    vix DOUBLE,
    vix_change_5d DOUBLE,
    fed_funds DOUBLE,
    -- Fundamental
    days_since_earnings INT,
    last_eps_surprise DOUBLE,
    -- Event
    earnings_within_7d BOOLEAN,
    PRIMARY KEY (symbol, date)
)
```

**Deliverable:** `scripts/feature_engine.py` + notebook to visualize features.

---

## Phase 3: Signal Generation

**Goal:** Define concrete "trading opportunity" hypotheses and compute signals.

### Approach: Start with simple, well-known strategies

Each strategy produces a daily score per stock: -1 (bearish) to +1 (bullish).

#### Strategy A: Momentum
- If 20d return > 0 AND price > MA50 AND relative strength vs SPY > 0: bullish
- Score = normalized momentum rank across universe

#### Strategy B: Mean Reversion
- If RSI < 30 AND price < lower Bollinger Band: bullish (oversold bounce)
- If RSI > 70 AND price > upper Bollinger Band: bearish (overbought)

#### Strategy C: Earnings Drift
- If last earnings surprise > 5% AND within 20 days of report: bullish drift
- If last earnings surprise < -5%: bearish drift

#### Strategy D: Macro Regime
- If VIX falling AND Fed steady AND SPY above MA50: "risk on" (favor growth stocks)
- If VIX rising AND yields rising: "risk off" (favor SPY, reduce exposure)

#### Strategy E: Earnings Straddle (event-driven)
- 3 days before expected earnings: flag as "high volatility event"
- This doesn't predict direction — it predicts magnitude
- Useful for options strategies (straddles) if we get options data working

### Output

A table `signals` with one row per (symbol, date, strategy):
```sql
CREATE TABLE signals (
    symbol TEXT,
    date DATE,
    strategy TEXT,
    score DOUBLE,        -- -1 to +1
    confidence DOUBLE,   -- 0 to 1
    PRIMARY KEY (symbol, date, strategy)
)
```

**Deliverable:** `scripts/signal_generator.py` + notebook demonstrating each signal.

---

## Phase 4: Backtesting Engine

**Goal:** Rigorously test whether signals predicted returns.

### Design Principles

1. **No look-ahead bias**: Only use information available at decision time
2. **Realistic execution**: Assume we buy at next day's open (not today's close)
3. **Include costs**: $0 commission but account for bid-ask spread (~0.05%)
4. **Out-of-sample testing**: Train on 2016-2022, test on 2023-2026

### Metrics to Compute

For each strategy:
- Total return
- Annualized return (using 365 calendar days)
- Sharpe ratio (return / volatility)
- Max drawdown
- Win rate (% of trades profitable)
- Average win vs average loss
- Return during "risk off" periods vs "risk on"
- Comparison vs buy-and-hold SPY

### Statistical Tests

- Is the strategy return statistically different from zero? (t-test)
- Does it survive transaction costs?
- Is it consistent across different time periods? (rolling window)
- Does it work for all stocks or just one?

### Output

A table `backtest_results`:
```sql
CREATE TABLE backtest_results (
    strategy TEXT,
    test_period TEXT,
    total_return DOUBLE,
    annualized_return DOUBLE,
    sharpe_ratio DOUBLE,
    max_drawdown DOUBLE,
    win_rate DOUBLE,
    num_trades INT,
    p_value DOUBLE,         -- statistical significance
    PRIMARY KEY (strategy, test_period)
)
```

**Deliverable:** `scripts/backtester.py` + detailed results notebook.

---

## Phase 5: Strategy Filtering (Self-Improvement)

**Goal:** Automatically reject strategies that don't meet quality thresholds.

### Filter Criteria

A strategy PASSES only if ALL of these hold:
1. Sharpe ratio > 0.5 (out-of-sample)
2. p-value < 0.05 (statistically significant)
3. Max drawdown < 30%
4. Works across at least 2 of 4 tickers
5. Consistent across 2+ test periods (no one-time fluke)
6. Beats SPY buy-and-hold after costs

### Overfitting Detection

- Compare in-sample vs out-of-sample performance
- If in-sample Sharpe > 2x out-of-sample Sharpe: likely overfit
- Test with randomized entry dates (Monte Carlo)
- Check if performance clusters around specific dates (data snooping)

### Strategy Evolution

For strategies that partially work:
- Vary parameters (e.g., 10-day vs 20-day momentum)
- Combine with regime filter (only trade in favorable macro)
- Add position sizing (bigger bets when confidence is high)

**Deliverable:** `scripts/strategy_filter.py` + survival report notebook.

---

## Phase 6: Paper Trading

**Goal:** Run surviving strategies live on Alpaca paper trading.

### Implementation

- Daily cron job after market close:
  1. Update data
  2. Compute features
  3. Generate signals
  4. Determine target positions
  5. Place orders via Alpaca paper trading API
  6. Log decisions and reasoning

- Track live performance vs backtest expectations
- Alert if live performance diverges significantly from backtest

### Position Sizing

- Max 25% of portfolio per position
- Total invested: 50-100% (keep some cash)
- Size proportional to signal confidence

**Deliverable:** `scripts/paper_trader.py` + daily log + performance dashboard.

---

## Phase 7: AI Research Agent

**Goal:** Use LLMs to propose new experiments and explain results.

### What the AI agent does:

1. **Performance review**: "Strategy B underperformed this week. Here's why..."
2. **Hypothesis generation**: "I notice NVDA moves more after earnings when VIX is elevated. Should we test a conditional straddle?"
3. **Feature suggestion**: "Adding sector rotation data might improve the regime filter."
4. **Anomaly detection**: "SPY dropped 3% but TSLA went up — unusual divergence worth investigating."

### How it works:

- Daily summary: AI reviews today's signals, positions, and outcomes
- Weekly review: AI analyzes what worked and what didn't
- Monthly experiment: AI proposes one new hypothesis to test

**Deliverable:** `scripts/research_agent.py` + weekly research memos.

---

## Implementation Timeline (ordered by dependency)

| Phase | Depends On | Focus |
|-------|-----------|-------|
| 2A: Technical features | Phase 1 | Pure computation from price data |
| 2B: Regime features | Phase 1 | Combine price + macro |
| 2C: Fundamental features | Phase 1 | Use earnings + SEC data |
| 3: Signals | Phase 2 | Define strategies |
| 4: Backtester | Phase 3 | Test strategies |
| 5: Filtering | Phase 4 | Keep only winners |
| 6: Paper trading | Phase 5 | Go live (paper) |
| 7: AI agent | Phase 6 | Self-improvement |

**Recommended order for next sessions:**
1. Phase 2A (technical features) — most impactful, pure code, no new data needed
2. Phase 4 (backtester skeleton) — can test simple strategies immediately
3. Phase 3 (signal generation) — define the strategies
4. Phase 5 (filtering) — apply rigor
5. Phase 6+7 — once you have surviving strategies

---

## Principles to Remember

1. **Simple beats complex.** A 3-feature model that works > a 100-feature model that's overfit.
2. **Out-of-sample or it doesn't count.** Never evaluate on training data.
3. **Markets change.** A strategy that worked 2018-2020 may not work 2024-2026.
4. **Transaction costs matter.** A strategy with 0.1% daily edge loses to spreads.
5. **Probability, not prediction.** We're looking for 55% win rates, not certainty.
6. **The null hypothesis is: this doesn't work.** Prove it wrong with data.
