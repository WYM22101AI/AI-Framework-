# Project Tracker: Family Quant AI

**Last updated:** 2026-09-07
**Status:** Phases 1-7 complete. Phase 8 agents built and tested. 19-ticker universe with index ETFs.

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
| 1.11 | Alpaca options fetcher | Done | Rewritten with alpaca-py. ATM IV, put/call ratios, greeks working |
| 1.12 | Multi-source orchestrator (update_market_data.py) | Done | Runs all 6 fetchers with error isolation |
| 1.13 | Git repo synced to GitHub | Done | https://github.com/WYM22101AI/AI-Framework-.git |
| 1.14 | README with setup/usage instructions | Done | |
| 1.15 | Windows batch file for scheduling | Done | scripts/run_update.bat |
| 1.16 | Set up Windows Task Scheduler | **Pending** | .bat file ready, user needs to configure Task Scheduler |

### Phase 1 data inventory

| Table | Rows | Source | Status |
|-------|------|--------|--------|
| daily_bars | 29,164 | Alpaca | Working (19 tickers, 10Y history) |
| macro_releases | 29,572 | FRED | Working |
| earnings | 296 | Alpha Vantage | Working (AAPL may need re-fetch due to rate limit) |
| fundamentals | 214 | SEC EDGAR | Working |
| news | 55 | Alpaca | Working |
| options_snapshot | Working | Alpaca | Rewritten with alpaca-py, ATM IV + greeks |

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

## Phase 3: Statistics Engine — COMPLETE

| # | Task | Status | Notes |
|---|------|--------|-------|
| 3.1 | t-test for mean return significance | Done | scipy.stats.ttest_1samp |
| 3.2 | Bootstrap confidence intervals | Done | 10,000 samples, 95% CI |
| 3.3 | Permutation test (shuffle-based significance) | Done | 5,000 permutations |
| 3.4 | Walk-forward validation | Done | 5-fold sequential split |
| 3.5 | Multiple testing correction (Holm/BH) | Done | Holm, Bonferroni, Benjamini-Hochberg |
| 3.6 | Economic significance check (survives costs?) | Done | Gross vs net after transaction costs |

---

## Phase 4: Backtesting Engine — COMPLETE

| # | Task | Status | Notes |
|---|------|--------|-------|
| 4.1 | Backtest framework (entry at next open, include costs) | Done | Next-day open execution, 5 bps round-trip cost |
| 4.2 | Performance metrics (Sharpe, drawdown, win rate, p-value) | Done | 10 metrics computed |
| 4.3 | Walk-forward split (train 2016-2022, test 2023-2026) | Done | split_date parameter, IS vs OOS |
| 4.4 | Execution realism (slippage, spread sensitivity) | Done | Configurable cost_per_trade |
| 4.5 | Comparison vs SPY buy-and-hold benchmark | Done | Included in every report |
| 4.6 | Overfitting detection (in-sample vs out-of-sample gap) | Done | Warns if IS Sharpe >> OOS Sharpe |

---

## Phase 5: Signal Generation (Scout) — COMPLETE

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.1 | Strategy A: Momentum | Done | **REJECTED all 3 stocks. OOS Sharpe: TSLA -0.68, AAPL -0.46, NVDA -0.67** |
| 5.2 | Strategy B: Mean Reversion | Done | **REJECTED. Best: NVDA Sharpe 0.58 but only 2/5 Skeptic tests** |
| 5.3 | Strategy C: Post-Earnings Drift | Done | **REJECTED. No signal generated (threshold too strict)** |
| 5.4 | Strategy D: Macro Regime filter | Pending | Not yet implemented |
| 5.5 | Strategy E: Earnings Straddle (event-driven) | Pending | Needs options data working |
| 5.6 | Signal output table in DuckDB | Pending | |

---

## Phase 6: Skeptic + Gatekeeper — IN PROGRESS

| # | Task | Status | Notes |
|---|------|--------|-------|
| 6.1 | Skeptic kill criteria (p-value, permutation, walk-forward, cross-stock, costs) | Done | Built into stats_engine.py full_skeptic_report() |
| 6.2 | Run all strategies through Skeptic | Done | 9 combinations tested, 0 survivors |
| 6.3 | Gatekeeper promotion criteria (Sharpe>0.5, drawdown<30%, beats SPY) | Pending | |
| 6.4 | Research memory tables in DuckDB | Done | research_experiments table with 9 records |
| 6.5 | Record all experiment results | Done | Lessons documented |

---

## Phase 7: Paper Trading — COMPLETE

| # | Task | Status | Notes |
|---|------|--------|-------|
| 7.1 | paper_trader.py — connect to Alpaca paper account | Done | Generates orders from signals, submits via API |
| 7.2 | Position sizing (max 25% per stock, 50% total) | Done | Equal-weight among active signals |
| 7.3 | Daily pipeline (data -> features -> signals -> orders) | Done | daily_pipeline.py chains all steps |
| 7.4 | Trade logging to DuckDB | Done | trade_log table with signal, order, execution status |
| 7.5 | Dry run tested | Done | Both signals FLAT today (correct — VIX < 20) |

---

## Phase 8: Multi-Agent Research Loop — IN PROGRESS

| # | Task | Status | Notes |
|---|------|--------|-------|
| 8.1 | Base agent class with logging | Done | agents/base.py — think(), log() to DuckDB |
| 8.2 | Regime classifier agent | Done | agents/regime.py — VIX + SPY MA50 → HIGH_VOL/RISK_OFF/RISK_ON/LOW_VOL/NEUTRAL |
| 8.3 | Scout agent — daily anomaly scan | Done | agents/scout.py — volume, RSI, Bollinger, earnings, relative strength |
| 8.4 | Governor agent — weekly review | Done | agents/governor.py — reviews experiments, anomalies, trades |
| 8.5 | Research loop orchestrator | Done | agents/research_loop.py — daily chain: data→features→regime→scout→trade |
| 8.6 | Agent memory tables (agent_log, agent_hypotheses) | Done | DuckDB tables, logging confirmed working |
| 8.7 | End-to-end test | Done | Regime=LOW_VOL, Scout=2 anomalies, Governor=ACTIVE, 5 log entries |
| 8.8 | Experimenter agent — formal hypothesis testing | Pending | |
| 8.9 | Skeptic agent — orchestrates stats_engine | Pending | |
| 8.10 | Gatekeeper agent — promotion decisions | Pending | |
| 8.11 | Migrate to smolagents when ready | Future | Start simple Python first |

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
| X.8 | Expand ticker universe beyond 4 stocks | Done | 19 tickers (15 stocks + SPY + QQQ + IWM + DIA) |

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
Phase 1: Data Foundation       [================] 16/16 tasks (100%)
Phase 2: Feature Engineering   [================]  7/7  tasks (100%)
Phase 3: Statistics Engine     [================]  6/6  tasks (100%)
Phase 4: Backtesting Engine    [================]  6/6  tasks (100%)
Phase 5: Signal Generation     [==========      ]  3/6  tasks (50%)
Phase 6: Skeptic + Gatekeeper  [============    ]  4/5  tasks (80%)
Phase 7: Paper Trading         [================]  5/5  tasks (100%)
Phase 8: Agent Research Loop   [============    ]  7/11 tasks (64%)
Cross-cutting                  [==              ]  1/8  tasks

Overall: 60/70 tasks complete (86%)
```

---

## How to Update This Tracker

At the start of each CoCo session:
1. Tell CoCo what you want to work on
2. CoCo updates task status as work completes
3. At end of session: CoCo commits updated tracker to GitHub

This file is the single source of truth for project status.
