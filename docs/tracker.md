# Project Tracker: Family Quant AI

**Last updated:** 2026-08-28
**Status:** Phase 1 & 2 complete, Phase 3 next

---

## Phase 1: Data Foundation — COMPLETE

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1.1 | Set up project structure (config, scripts, storage) | Done | Restructured 2026-08-20 |
| 1.2 | Alpaca stock price fetcher | Done | 4 tickers, ~6 years daily bars |
| 1.3 | DuckDB storage with upsert logic | Done | Primary keys, dedup on insert |
| 1.4 | Incremental update logic | Done | Only fetches data newer than stored |
| 1.5 | .env-based secrets management | Done | .env.example committed, .env gitignored |
| 1.6 | requirements.txt | Done | alpaca-py, alpaca-trade-api, duckdb, pandas, fredapi, requests |
| 1.7 | FRED macro data fetcher | Done | 8 series, 29,572 observations |
| 1.8 | Alpha Vantage earnings fetcher | Done | 296 quarters (TSLA, NVDA) |
| 1.9 | SEC EDGAR fundamentals fetcher | Done | 214 filings (TSLA, AAPL, NVDA) |
| 1.10 | Alpaca news fetcher | Done | 55 recent articles |
| 1.11 | Alpaca options fetcher | **Broken** | `alpaca-trade-api` has no `get_option_chain`. Needs migration to `alpaca-py` OptionHistoricalDataClient |
| 1.12 | Multi-source orchestrator (update_market_data.py) | Done | Runs all 6 fetchers with error isolation |
| 1.13 | Git repo synced to GitHub | Done | https://github.com/WYM22101AI/AI-Framework-.git |
| 1.14 | README with setup/usage instructions | Done | |
| 1.15 | Windows batch file for scheduling | Done | scripts/run_update.bat |
| 1.16 | Set up Windows Task Scheduler | **Pending** | .bat file ready, user needs to configure Task Scheduler |

### Phase 1 data inventory

| Table | Rows | Source | Status |
|-------|------|--------|--------|
| daily_bars | 6,113 | Alpaca | Working |
| macro_releases | 29,572 | FRED | Working |
| earnings | 296 | Alpha Vantage | Working (AAPL may need re-fetch due to rate limit) |
| fundamentals | 214 | SEC EDGAR | Working |
| news | 55 | Alpaca | Working |
| options_snapshot | 0 | Alpaca | Broken — needs API client fix |

---

## Phase 2: Feature Engineering — COMPLETE

| # | Task | Status | Notes |
|---|------|--------|-------|
| 2.1 | Technical features (returns, volatility, RSI, Bollinger, MA distances) | Done | feature_engine.py |
| 2.2 | Relative strength vs SPY | Done | Included in feature_engine.py |
| 2.3 | Store features in DuckDB `daily_features` table | Done | 3,996 rows persisted with upsert |
| 2.4 | Regime features (VIX level, yield curve, Fed direction) | Done | VIX, VIX 5d change, Fed funds, 10Y Treasury |
| 2.5 | Fundamental features (days since earnings, EPS surprise) | Done | days_since_earnings, last_eps_surprise |
| 2.6 | Event features (earnings within 7 days flag) | Done | earnings_within_7d boolean |
| 2.7 | Feature visualization notebook | Done | 6 technical charts + 4 regime charts + earnings bar chart |

---

## Phase 3: Statistics Engine — NOT STARTED

| # | Task | Status | Notes |
|---|------|--------|-------|
| 3.1 | t-test for mean return significance | Pending | Use scipy.stats |
| 3.2 | Bootstrap confidence intervals | Pending | |
| 3.3 | Permutation test (shuffle-based significance) | Pending | |
| 3.4 | Walk-forward validation | Pending | Rolling out-of-sample splits |
| 3.5 | Multiple testing correction (Holm/BH) | Pending | Prevent data snooping |
| 3.6 | Economic significance check (survives costs?) | Pending | |

---

## Phase 4: Backtesting Engine — NOT STARTED

| # | Task | Status | Notes |
|---|------|--------|-------|
| 4.1 | Backtest framework (entry at next open, include costs) | Pending | Adopt Alpaca Skills methodology |
| 4.2 | Performance metrics (Sharpe, drawdown, win rate, p-value) | Pending | |
| 4.3 | Walk-forward split (train 2016-2022, test 2023-2026) | Pending | |
| 4.4 | Execution realism (slippage, spread sensitivity) | Pending | |
| 4.5 | Comparison vs SPY buy-and-hold benchmark | Pending | |
| 4.6 | Overfitting detection (in-sample vs out-of-sample gap) | Pending | |

---

## Phase 5: Signal Generation (Scout) — NOT STARTED

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.1 | Strategy A: Momentum (20d return + MA50 + relative strength) | Pending | Simplest hypothesis |
| 5.2 | Strategy B: Mean Reversion (RSI + Bollinger) | Pending | |
| 5.3 | Strategy C: Post-Earnings Drift | Pending | Needs earnings dates + price data |
| 5.4 | Strategy D: Macro Regime filter | Pending | Needs regime features |
| 5.5 | Strategy E: Earnings Straddle (event-driven) | Pending | Needs options data working |
| 5.6 | Signal output table in DuckDB | Pending | |

---

## Phase 6: Skeptic + Gatekeeper — NOT STARTED

| # | Task | Status | Notes |
|---|------|--------|-------|
| 6.1 | Skeptic kill criteria (p-value, permutation, walk-forward, cross-stock, costs) | Pending | |
| 6.2 | Run all strategies through Skeptic | Pending | |
| 6.3 | Gatekeeper promotion criteria (Sharpe>0.5, drawdown<30%, beats SPY) | Pending | |
| 6.4 | Research memory tables in DuckDB | Pending | hypotheses, experiments, results, lessons |
| 6.5 | Record all experiment results | Pending | |

---

## Phase 7: Paper Trading — NOT STARTED

| # | Task | Status | Notes |
|---|------|--------|-------|
| 7.1 | paper_trader.py — connect to Alpaca paper account | Pending | |
| 7.2 | Daily automated workflow (data -> features -> signals -> orders) | Pending | |
| 7.3 | Performance dashboard | Pending | |
| 7.4 | Position sizing (volatility-adjusted, max 25%) | Pending | |
| 7.5 | Live vs backtest performance tracking | Pending | |

---

## Phase 8: Multi-Agent Research Loop — NOT STARTED

| # | Task | Status | Notes |
|---|------|--------|-------|
| 8.1 | Install and configure smolagents (HuggingFace) | Pending | |
| 8.2 | Scout agent — daily anomaly scan | Pending | |
| 8.3 | Context/Regime agent — market state classification | Pending | |
| 8.4 | Feature Miner agent — propose new features | Pending | |
| 8.5 | Skeptic agent — orchestrates stats_engine | Pending | |
| 8.6 | Experimenter agent — formal experiment design | Pending | |
| 8.7 | Gatekeeper agent — promotion decisions | Pending | |
| 8.8 | Governor agent — research agenda, weekly review | Pending | |
| 8.9 | Connect agents to research memory | Pending | |
| 8.10 | First end-to-end agent research cycle | Pending | |
| 8.11 | Quarterly meta-review capability | Pending | |

---

## Cross-Cutting Tasks

| # | Task | Status | Notes |
|---|------|--------|-------|
| X.1 | Study reference repos (TradingAgents, quant-agent, etc.) | **Pending** | Ask CoCo to analyze, don't clone into repo |
| X.2 | Review Alpaca Skills library | **Pending** | Identify SKILL.md files to adopt |
| X.3 | Create docs/references/ directory with provenance docs | **Pending** | |
| X.4 | HuggingFace Agents Course (reference material) | **Pending** | Use as reference while building agents |
| X.5 | Rotate exposed Alpaca API keys | **Pending** | Old keys in git history — rotate in Alpaca dashboard |
| X.6 | Pin all dependency versions in requirements.txt | **Pending** | Currently using >= ranges, should pin exact |
| X.7 | Evaluate cloud migration trigger (Snowflake) | Future | When local compute becomes bottleneck |
| X.8 | Expand ticker universe beyond 4 stocks | Future | After strategies validated on initial universe |

---

## Blockers and Risks

| Issue | Impact | Mitigation |
|-------|--------|-----------|
| Options fetcher broken (alpaca-trade-api lacks get_option_chain) | Can't test Strategy E (earnings straddle), no options features | Fix in Week 1-2: switch to alpaca-py OptionHistoricalDataClient |
| AAPL earnings may not have loaded (Alpha Vantage rate limit) | Incomplete earnings data | Re-run fetcher; Alpha Vantage allows 25 calls/day |
| Alpaca free tier IEX data only goes back to ~2016 | Can't backtest pre-2016 strategies | Sufficient for our purposes; add Massive later if needed |
| smolagents is experimental (HuggingFace) | Agent framework could change | Keep core logic in plain Python; smolagents is replaceable orchestration |
| One hour per day is limited | Progress will be incremental | CoCo does the coding; you provide direction and review |

---

## Progress Summary

```
Phase 1: Data Foundation       [================] 14/16 tasks (88%)
Phase 2: Feature Engineering   [================]  7/7  tasks (100%)
Phase 3: Statistics Engine     [                ]  0/6  tasks
Phase 4: Backtesting Engine    [                ]  0/6  tasks
Phase 5: Signal Generation     [                ]  0/6  tasks
Phase 6: Skeptic + Gatekeeper  [                ]  0/5  tasks
Phase 7: Paper Trading         [                ]  0/5  tasks
Phase 8: Agent Research Loop   [                ]  0/11 tasks
Cross-cutting                  [                ]  0/8  tasks

Overall: 21/70 tasks complete (30%)
```

---

## How to Update This Tracker

At the start of each CoCo session:
1. Tell CoCo what you want to work on
2. CoCo updates task status as work completes
3. At end of session: CoCo commits updated tracker to GitHub

This file is the single source of truth for project status.
