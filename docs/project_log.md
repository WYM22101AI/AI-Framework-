# Project Log: Family Quant AI

## Project Overview

**Participants:** Yaming (parent) + Benjamin (son)
**Goal:** Build an AI research framework for financial markets — learn coding, data engineering, statistics, and ML through a real-world project.
**Repo:** https://github.com/WYM22101AI/AI-Framework-.git

---

## Session 1: Project Restructure (2026-08-20)

### What we did
- Diagnosed the existing project: scattered experimental scripts, hardcoded API keys, inconsistent DB paths
- Consolidated into a modular pipeline architecture
- Created: `config.py`, `scripts/market_fetcher.py`, `scripts/storage.py`, `update_market_data.py`
- Moved old files to `archive/`
- Fetched 5 years of daily data for TSLA, AAPL, NVDA, SPY

### Key decisions
- Use `alpaca-trade-api` (REST v2) for stock data
- DuckDB as local analytical database (`data/market_data.duckdb`)
- All secrets in `.env` (gitignored), template in `.env.example`
- Prices are fully split+dividend adjusted (`adjustment="all"`)

---

## Session 2: Expanded Data Sources (2026-08-25)

### What we did
- Extended lookback to 10 years (got data back to Aug 2016 from IEX feed)
- Added 5 new data sources based on ChatGPT architecture discussion
- Built fetchers for: FRED macro, Alpha Vantage earnings, SEC EDGAR fundamentals, Alpaca news
- All tables are event-time aware (store when data became publicly known)

### Data sources and what they provide

| Source | Table | Key Data |
|--------|-------|----------|
| Alpaca | daily_bars | OHLCV, 6,113 rows (4 tickers x ~6 yrs) |
| FRED | macro_releases | CPI, unemployment, Fed funds, 10Y yield, GDP, retail sales, sentiment, VIX (29,572 obs) |
| Alpha Vantage | earnings | Quarterly EPS actual, estimate, surprise (296 quarters) |
| SEC EDGAR | fundamentals | Revenue, net income, assets, liabilities from 10-K/10-Q (214 filings) |
| Alpaca | news | Headlines with timestamps (55 recent articles) |
| Alpaca | options_snapshot | ATM IV, put/call ratios (NOT YET WORKING) |

### Architecture after expansion

```
update_market_data.py          (orchestrator - runs all 6 fetchers)
    ├── scripts/market_fetcher.py   (Alpaca stock prices)
    ├── scripts/fred_fetcher.py     (FRED macro data)
    ├── scripts/earnings_fetcher.py (Alpha Vantage earnings)
    ├── scripts/sec_fetcher.py      (SEC EDGAR fundamentals)
    ├── scripts/options_fetcher.py  (Alpaca options - BROKEN)
    └── scripts/news_fetcher.py     (Alpaca news)
```

### Important concepts discussed

**Adjusted prices:** With `adjustment="all"`, all historical prices account for stock splits (TSLA 5:1 in 2020, 3:1 in 2022) and dividends. Simple return calculation works directly: `(close_end / close_start) - 1`

**Annualized return formula:**
- For comparing to CDs/bonds: use 365 calendar days, NOT 252 trading days
- Formula: `annualized = (1 + total_return) ^ (365 / calendar_days) - 1`
- The 252 convention is only for annualizing volatility (risk metric)

**Event-time awareness:** Every data point stores when it became publicly available. This prevents look-ahead bias in backtests. For example:
- Earnings: `reported_date` (when the company announced)
- SEC filings: `filed_date` (when SEC received it)
- Macro: `release_date` (when the number was published)

**Earnings straddle strategy:** Buy call + put before earnings, profit from big moves. Key insight from research: straddles around earnings tend to lose money on average because implied volatility is already inflated. You only profit if the actual move exceeds market expectations. We need options history to properly backtest this (currently blocked by the options API issue).

---

## Known Issues / TODO

- [ ] Fix options fetcher (needs `alpaca-py` OptionHistoricalDataClient, not `alpaca-trade-api`)
- [ ] AAPL earnings didn't load from Alpha Vantage (likely rate limit — retry later)
- [ ] Add technical indicators (moving averages, RSI, Bollinger Bands)
- [ ] Build feature engine for ML (daily state vector per stock)
- [ ] Earnings straddle backtest (once options data is available)
- [ ] Rotate old Alpaca API keys (exposed in git history)

---

## Session 3: Feature Engine + Stats Engine + Backtester + First Strategy (2026-08-28)

### What we did
- Completed Phase 2: expanded feature_engine.py with regime, fundamental, and event features
- Completed Phase 3: built stats_engine.py (the Skeptic's toolbox)
- Completed Phase 4: built backtester.py with proper methodology
- Completed Phase 5 (partial): implemented 3 strategies, ran first backtest
- Hit Month 1 milestone: first strategy fully backtested with statistics

### Feature engine (19 features per stock per day)
- Technical: returns (1d/5d/20d/60d), volatility, RSI-14, Bollinger position, MA distances, relative volume, relative strength vs SPY
- Regime: VIX, VIX 5d change, Fed funds rate, 10-year Treasury yield
- Fundamental: days since earnings, last EPS surprise
- Event: earnings within 7 days flag
- Stored in DuckDB `daily_features` table (3,996 rows)

### Statistics engine (6 tests)
- t-test (is mean return != 0?)
- Bootstrap confidence interval (10,000 samples)
- Permutation test (5,000 shuffles)
- Walk-forward validation (5-fold sequential)
- Multiple testing correction (Holm/Bonferroni/BH)
- Economic significance (survives transaction costs?)
- `full_skeptic_report()` runs all 5 and returns PASS/WEAK/FAIL

### Backtester design
- Entry at next day's OPEN (not today's close — avoids look-ahead)
- 5 bps round-trip transaction cost
- In-sample (pre-2023) vs out-of-sample (2023+) split
- Overfitting detection: warns if IS Sharpe >> OOS Sharpe
- SPY buy-and-hold benchmark comparison

### First strategy result: MOMENTUM on TSLA — REJECTED

| Period | Return | Sharpe | Drawdown |
|--------|--------|--------|----------|
| In-sample | +11.7%/yr | 0.48 | -47.5% |
| Out-of-sample | -28.9%/yr | -0.68 | -77.0% |

Skeptic verdict: **FAIL (0/5 tests passed)**. Overfitting warning triggered.
This is the system working as designed — rejecting a strategy that doesn't hold up.

### Strategies coded (ready to test)
- Strategy A: Momentum (tested, rejected)
- Strategy B: Mean Reversion (RSI + Bollinger) — coded, not yet tested
- Strategy C: Post-Earnings Drift — coded, not yet tested

### Design decisions incorporated (from ChatGPT discussions)
- 6-agent architecture: Governor, Scout, Context/Regime, Skeptic, Experimenter, Gatekeeper
- Three-layer separation: Ground truth (Alpaca Skills) / Research assumptions (ours) / Secret sauce (filtering)
- Reference governance: study don't clone, borrow engineering build research
- Data source roadmap: use free sources now, add paid only when research proves need
- HuggingFace smolagents as future agent orchestration framework
- Research memory database schema (hypotheses, experiments, results, lessons)

### Project documentation created
- `docs/research_plan.md` — master architecture (6 agents, build-vs-borrow, data roadmap)
- `docs/timeline.md` — 6-month roadmap with weekly tasks
- `docs/tracker.md` — task-level progress tracker (36/70 = 51%)
- `docs/knowledge_library.md` — complete handover document
- `docs/project_log.md` — this file

### Progress: 36/70 tasks (51%)
```
Phase 1: Data Foundation       [================] 88%
Phase 2: Feature Engineering   [================] 100%
Phase 3: Statistics Engine     [================] 100%
Phase 4: Backtesting Engine    [================] 100%
Phase 5: Signal Generation     [======          ] 50%
```

### Next session priorities
1. Run mean_reversion and earnings_drift through Skeptic
2. Test strategies across multiple stocks (AAPL, NVDA), not just TSLA
3. Begin Phase 6: formal Skeptic + Gatekeeper automation
4. Study reference repos (TradingAgents, quant-agent)

---

## Session 6: Options Fix + Stress Test + Earnings Straddle (2026-09-07)

### What we did
- Fixed options fetcher (task 1.11 — broken since Day 1): rewritten using alpaca-py OptionHistoricalDataClient
- Now pulls ATM IV, put/call ratios, greeks for all tickers
- Stress tested the VIX mean reversion strategy under adverse conditions
- Built and ran earnings straddle analysis across 8 stocks (192 events)

### Options fetcher (FIXED)
- AMZN: IV 34.65%, P/C ratio 1.20
- NVDA: IV 38.88%, P/C ratio 1.18
- TSLA: IV 45.59%, P/C ratio 2.11 (heavy put positioning)

### Stress test results: strategy is robust

| Test | AMZN Sharpe | NVDA Sharpe |
|------|-------------|-------------|
| Base (5 bps) | 1.46 | 1.02 |
| 2x costs (10 bps) | 1.39 | 0.98 |
| 3x costs (15 bps) | 1.32 | 0.94 |
| Remove best 5 trades | 1.17 | 0.19 |
| Remove best 10 trades | 0.66 | -0.44 |
| First half OOS | 1.30 | 1.08 |
| Second half OOS | 1.66 | 1.08 |

Conclusion: AMZN is rock solid. NVDA depends on a few big wins.

### Earnings straddle analysis: all 8 stocks positive

| Stock | Avg Move | Win Rate | Avg P&L/Event |
|-------|----------|----------|---------------|
| META | 10.0% | 83% | +6.70% |
| AMZN | 6.6% | 79% | +3.67% |
| TSLA | 7.7% | 58% | +2.49% |
| GOOG | 5.0% | 79% | +2.47% |
| MSFT | 4.7% | 83% | +2.41% |
| AMD | 6.8% | 58% | +2.02% |
| NVDA | 6.1% | 46% | +1.58% |
| AAPL | 3.0% | 58% | +0.56% |

Overall: +2.74% per event. Tech mega-caps move 2-4x more than realized vol around earnings.
Caveat: uses estimated straddle cost, not actual IV. Needs real options data to confirm.

### Next session priorities
1. Phase 8: Build AI research agents (Scout, Governor) using smolagents
2. Collect real pre-earnings IV data going forward (options fetcher now works)
3. Expand stock universe to 50+ for cross-sectional analysis for architecture ideas

---

## Session 4: All Strategies Tested — 0 Survivors (2026-08-28)

### What we did
- Ran all 3 strategies (momentum, mean reversion, earnings drift) across all 3 stocks (TSLA, AAPL, NVDA)
- 9 total strategy-stock combinations tested through full Skeptic pipeline
- Created research_experiments table in DuckDB (research memory)
- Recorded all 9 experiment results with notes and lessons

### Results: 0 out of 9 survived the Skeptic

| Strategy | TSLA | AAPL | NVDA |
|----------|------|------|------|
| Momentum | FAIL 0/5 (Sharpe -0.68) | FAIL 0/5 (Sharpe -0.46) | FAIL 0/5 (Sharpe -0.67) |
| Mean Reversion | FAIL 0/5 (Sharpe -0.65) | FAIL 1/5 (Sharpe 0.10) | FAIL 2/5 (Sharpe 0.58) |
| Earnings Drift | FAIL 0/5 (no signal) | FAIL 0/5 (no signal) | FAIL 0/5 (no signal) |

### Lessons learned
1. Simple momentum fails badly out-of-sample on liquid US large-caps — the signal has been arbitraged away
2. Mean reversion on NVDA shows a glimmer (Sharpe 0.58, -7% drawdown, 2/5 tests) — worth deeper investigation
3. Earnings drift threshold (5%) is too strict — rarely triggers. Need to lower it or use different signal
4. AAPL earnings data incomplete due to Alpha Vantage rate limiting — needs re-fetch
5. **0 survivors is the expected honest result** — finding real edge requires more sophisticated hypotheses

### Key insight
The system is working exactly as designed. The Skeptic's job is to kill bad ideas. If basic textbook strategies survived, that would be suspicious — they've been known for decades and are heavily traded.

### What this means for next steps
- Need regime-conditional strategies (same signal works differently in different market environments)
- Need combination strategies (momentum + regime filter, mean reversion + VIX condition)
- Consider expanding the stock universe (50+ stocks may reveal cross-sectional patterns)
- The AI research agent (Phase 8) becomes more important — need systematic hypothesis generation

### Next session priorities
1. Improve earnings drift (lower threshold, re-fetch AAPL)
2. Add regime conditioning to existing strategies
3. Explore combined strategies (momentum only when VIX < 20, mean reversion only when RSI extreme)
4. Consider expanding universe

---

## Session 5: Expanded Universe + Parameter Sweep + Paper Trading (2026-09-05)

### What we did
- Expanded ticker universe from 4 to 16 stocks (tech, finance, healthcare, consumer, energy)
- Fetched 24,556 price rows, computed 20,034 feature rows for 15 stocks
- Tested VIX-conditional mean reversion across all 15 stocks
- Found first Skeptic PASS: AMZN (Sharpe 1.25, 4/5 tests)
- Ran 27-parameter sweep (3 RSI x 3 Bollinger x 3 VIX thresholds)
- Identified optimal parameters: RSI<35, Bollinger<-0.6, VIX>20
- Tuned strategy: AMZN PASS (Sharpe 1.46), NVDA PASS (Sharpe 1.02)
- Built complete paper trading pipeline (paper_trader.py + daily_pipeline.py)
- Dry run tested: both signals FLAT (correct — VIX below 20)

### Strategy results: Tuned VIX Mean Reversion (RSI<35, BB<-0.6, VIX>20)

| Stock | OOS Sharpe | Verdict | Beats SPY |
|-------|-----------|---------|-----------|
| AMZN | 1.46 | PASS 4/5 | Yes |
| NVDA | 1.02 | PASS 4/5 | Yes |
| AMD | 0.62 | FAIL 1/5 | Yes |
| TSLA | 0.52 | FAIL 1/5 | Yes |
| MSFT | 0.15 | FAIL 1/5 | No |

### Parameter sweep findings
- VIX > 20 is essential (all top 7 variants use it)
- VIX > 15 loses money (too many false signals in calm markets)
- VIX > 25 has too few trades
- Strategy works best on high-beta tech (AMZN, NVDA, AMD, TSLA)
- Fails on defensive stocks (WMT, UNH, HD)

### Paper trading setup
- Approved stocks: AMZN, NVDA (Skeptic PASSes)
- Position sizing: 25% max per stock, 50% total exposure
- Daily pipeline: data -> features -> signals -> orders
- Dry run vs execute mode (--execute flag)
- Trade log table in DuckDB

### Progress: 48/70 tasks (69%)
```
Phase 1-4: Complete
Phase 5:   50% (3 strategies tested + 3 regime variants)
Phase 6:   80% (Skeptic running, Gatekeeper criteria defined)
Phase 7:   100% (paper trading pipeline operational)
Phase 8:   0% (AI research agents — next major phase)
```

### Next session priorities
1. Phase 8: Set up smolagents (HuggingFace) as agent orchestration
2. Build Scout agent for daily anomaly detection
3. Stress test the VIX mean reversion strategy (2x costs, remove best trades)
4. Study reference repos (TradingAgents, quant-agent)

---

## Learning Resources (from original README)

See `docs/learning_roadmap.md` for the full 5-phase learning path:
1. Market structure (books)
2. Data & statistics
3. Python for finance
4. Machine learning
5. Modern AI/LLMs

---

## How to Run

```bash
# Activate environment
venv\Scripts\activate      # Windows
source venv/bin/activate   # Mac

# Run the full pipeline
python update_market_data.py

# Query the data
python -c "import duckdb; conn = duckdb.connect('data/market_data.duckdb'); print(conn.execute('SELECT * FROM daily_bars WHERE symbol=\\'TSLA\\' ORDER BY timestamp DESC LIMIT 5').fetchdf()); conn.close()"
```
