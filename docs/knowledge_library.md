# Knowledge Library: Family Quant AI

**Purpose:** Reference for anyone (Yaming, Benjamin, CoCo, or any future AI agent) picking up this project.

---

## 1. What This Project Is

A father-son learning project that builds an AI-assisted quantitative research platform. It collects financial market data, generates trading hypotheses, tests them with rigorous statistics, and runs surviving strategies on paper trading via Alpaca.

**It is NOT a get-rich-quick trading bot.** It's a research system that gets smarter over time.

**Participants:**
- Yaming Wang (parent) — project lead, ~1 hour/day
- Benjamin (son) — learning partner, occasional sessions
- CoCo (Cortex Code) — AI coding assistant, does the heavy lifting
- Future: smolagents-based research agents (Scout, Skeptic, Governor, etc.)

**Repository:** https://github.com/WYM22101AI/AI-Framework-.git

---

## 2. How to Set Up From Scratch

### Prerequisites
- Python 3.10+ installed
- Git installed
- Alpaca paper trading account (free): https://app.alpaca.markets
- FRED API key (free): https://fred.stlouisfed.org/docs/api/api_key.html
- Alpha Vantage API key (free): https://www.alphavantage.co/support/#api-key

### Steps

```bash
# Clone
git clone https://github.com/WYM22101AI/AI-Framework-.git family-quant-ai
cd family-quant-ai

# Virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac

# Dependencies
pip install -r requirements.txt

# API keys — create .env from template
cp .env.example .env
# Edit .env and add your keys:
#   APCA_API_KEY=...
#   APCA_API_SECRET=...
#   FRED_API_KEY=...
#   ALPHA_VANTAGE_API_KEY=...

# Fetch all data (takes ~2 minutes, Alpha Vantage is slow due to rate limits)
python update_market_data.py

# Verify
python -c "import duckdb; conn = duckdb.connect('data/market_data.duckdb'); print(conn.execute('SHOW TABLES').fetchall()); conn.close()"
```

---

## 3. Project Structure

```
family-quant-ai/
|-- config.py                  # All settings: API keys, tickers, DB path, FRED series
|-- update_market_data.py      # Main pipeline: runs all 6 data fetchers
|-- requirements.txt           # Python dependencies
|-- .env                       # API keys (NOT in git)
|-- .env.example               # Template for .env
|
|-- scripts/
|   |-- market_fetcher.py      # Alpaca daily stock bars
|   |-- fred_fetcher.py        # FRED macro economic data
|   |-- earnings_fetcher.py    # Alpha Vantage quarterly earnings
|   |-- sec_fetcher.py         # SEC EDGAR company fundamentals
|   |-- options_fetcher.py     # Alpaca options (BROKEN - needs fix)
|   |-- news_fetcher.py        # Alpaca news headlines
|   |-- storage.py             # DuckDB table creation and upsert operations
|   |-- feature_engine.py      # Computes technical features from price data
|   |-- signal_generator.py    # Placeholder: Phase 5
|   |-- backtester.py          # Placeholder: Phase 4
|   |-- strategy_filter.py     # Placeholder: Phase 5
|   +-- __init__.py
|
|-- data/
|   +-- market_data.duckdb     # Local database (NOT in git)
|
|-- notebooks/
|   +-- exploration.ipynb      # Interactive data exploration
|
|-- docs/
|   |-- research_plan.md       # Master architecture and design document
|   |-- timeline.md            # 6-month project timeline with weekly tasks
|   |-- tracker.md             # Task-level progress tracker
|   |-- project_log.md         # Session-by-session history
|   |-- learning_roadmap.md    # Educational resources and reading list
|   +-- knowledge_library.md   # THIS FILE — handover document
|
+-- archive/                   # Old experimental scripts (reference only)
```

---

## 4. Database Schema

All data lives in `data/market_data.duckdb`. Tables:

### daily_bars (stock prices)
```sql
-- Source: Alpaca API (IEX feed, split+dividend adjusted)
-- Updated: daily after market close
-- Primary key: (symbol, timestamp)
symbol TEXT, timestamp TIMESTAMPTZ, open DOUBLE, high DOUBLE, low DOUBLE,
close DOUBLE, volume DOUBLE, trade_count DOUBLE, vwap DOUBLE
```

### macro_releases (economic indicators)
```sql
-- Source: FRED API
-- Series: CPIAUCSL, UNRATE, FEDFUNDS, DGS10, GDP, RSAFS, UMCSENT, VIXCLS
-- Primary key: (series_id, observation_date)
series_id TEXT, observation_date DATE, release_date DATE, value DOUBLE
```

### earnings (quarterly EPS)
```sql
-- Source: Alpha Vantage EARNINGS endpoint
-- Primary key: (symbol, fiscal_date_ending)
symbol TEXT, fiscal_date_ending DATE, reported_date DATE,
reported_eps DOUBLE, estimated_eps DOUBLE, surprise DOUBLE, surprise_pct DOUBLE
```

### fundamentals (SEC filings)
```sql
-- Source: SEC EDGAR XBRL API (data.sec.gov)
-- CIK mapping: TSLA=0001318605, AAPL=0000320193, NVDA=0001045810
-- Primary key: (symbol, fiscal_date_ending)
symbol TEXT, fiscal_date_ending DATE, filed_date DATE,
revenue DOUBLE, net_income DOUBLE, total_assets DOUBLE,
total_liabilities DOUBLE, operating_cash_flow DOUBLE
```

### options_snapshot (NOT YET WORKING)
```sql
-- Source: Alpaca options API
-- Primary key: (symbol, snapshot_date)
symbol TEXT, snapshot_date DATE, atm_iv DOUBLE,
put_call_volume_ratio DOUBLE, put_call_oi_ratio DOUBLE,
total_call_volume BIGINT, total_put_volume BIGINT
```

### news (headlines)
```sql
-- Source: Alpaca news API
-- Primary key: (id, symbol)
id TEXT, symbol TEXT, headline TEXT, published_at TIMESTAMPTZ, source TEXT
```

---

## 5. Key Technical Decisions (and why)

### Why DuckDB (not Postgres/SQLite)?
- Analytical workload (column-oriented scans, aggregations)
- Zero setup (single file, no server)
- Direct pandas integration (register DataFrames as tables)
- Handles millions of rows on a laptop
- Can migrate to Snowflake later if needed

### Why alpaca-trade-api (not alpaca-py)?
- Better multi-symbol support for `get_bars()`
- Simpler REST API for our use case
- **Exception:** Options need `alpaca-py` (the newer SDK) — that's why options_fetcher is broken

### Why adjustment="all" for stock prices?
- Retroactively adjusts for stock splits AND dividends
- Tesla had 5:1 split (Aug 2020) and 3:1 split (Aug 2022)
- With adjusted prices, return = (close_end / close_start) - 1. No extra math needed.

### Why 365 calendar days for annualized returns (not 252 trading days)?
- 252 is for annualizing VOLATILITY (risk metric)
- 365 is for annualizing RETURNS (comparable to CDs, bonds, savings accounts)
- Formula: `annualized = (1 + total_return) ** (365 / calendar_days) - 1`

### Why event-time awareness?
- Every table stores WHEN information became public (reported_date, filed_date, release_date)
- Prevents look-ahead bias in backtests
- If CPI was released on July 15, our backtest can't use it on July 14

---

## 6. How the Daily Pipeline Works

```
update_market_data.py
    |
    |-- [1/6] Stock prices (Alpaca)
    |   Checks last stored date per ticker, fetches only new data
    |
    |-- [2/6] Macro data (FRED)
    |   Fetches 8 economic series, stores with observation dates
    |
    |-- [3/6] Earnings (Alpha Vantage)
    |   Quarterly EPS for TSLA, AAPL, NVDA (skips SPY — it's an ETF)
    |   Rate limited: 12-second sleep between tickers
    |
    |-- [4/6] Fundamentals (SEC EDGAR)
    |   XBRL financial data, deduped by latest filing per fiscal period
    |   Rate limited: 0.2s between calls
    |
    |-- [5/6] Options (Alpaca) — CURRENTLY BROKEN
    |
    |-- [6/6] News (Alpaca)
    |   Last 7 days of headlines for all tickers
    |
    +-- Prints database summary
```

Each fetcher is wrapped in try/except so one failure doesn't crash the pipeline.

---

## 7. Known Issues

| Issue | Details | Fix |
|-------|---------|-----|
| Options fetcher broken | `alpaca-trade-api` REST client has no `get_option_chain` method | Rewrite using `alpaca-py` OptionHistoricalDataClient |
| AAPL earnings incomplete | Alpha Vantage may have rate-limited the request | Re-run; only 4 calls needed (25/day limit) |
| Old API keys in git history | `Check Python DB.py` had plaintext keys before archiving | Rotate keys in Alpaca dashboard |
| Task Scheduler not configured | .bat file exists but scheduler not set up | Manual setup: Task Scheduler > Daily 5PM > run_update.bat |

---

## 8. Configuration Reference

### config.py settings

```python
API_KEY          # Alpaca API key (from .env)
API_SECRET       # Alpaca API secret (from .env)
BASE_URL         # "https://paper-api.alpaca.markets"
FEED             # "iex" (free tier)
FRED_API_KEY     # FRED API key (from .env)
FRED_SERIES      # ["CPIAUCSL", "UNRATE", "FEDFUNDS", "DGS10", "GDP", "RSAFS", "UMCSENT", "VIXCLS"]
ALPHA_VANTAGE_API_KEY  # Alpha Vantage key (from .env)
SEC_USER_AGENT   # "FamilyQuantAI yamingwang@gmail.com"
DB_PATH          # Auto-resolved to data/market_data.duckdb
TICKERS          # ["TSLA", "AAPL", "NVDA", "SPY"]
LOOKBACK_YEARS   # 10
```

### API rate limits

| API | Limit | Our usage |
|-----|-------|-----------|
| Alpaca (prices) | 200/min | 4 tickers — no issue |
| Alpaca (news) | 200/min | 1 call — no issue |
| FRED | 120/min | 8 series — no issue |
| Alpha Vantage | 25/day, ~5/min | 3 tickers (skip SPY) with 12s sleep |
| SEC EDGAR | 10/sec | 3 tickers with 0.2s sleep |

---

## 9. Design Philosophy

Read `docs/research_plan.md` for the full architecture. Key principles:

1. **LLMs reason, code calculates.** AI generates hypotheses; Python tests them with statistics.
2. **The Skeptic is the most valuable agent.** Its job is to kill bad ideas.
3. **Out-of-sample or it doesn't count.** Never evaluate on training data.
4. **Every data source must earn its place.** Prove it adds value before making it permanent.
5. **Borrow engineering, build research.** Use standard libraries for standard things; our edge is the filtering.
6. **The platform is the product.** Profitable strategies are a bonus; the learning is the goal.

---

## 10. Document Map

| Document | Purpose | When to read |
|----------|---------|-------------|
| `docs/knowledge_library.md` | **THIS FILE** — complete project context for handover | First, always |
| `docs/tracker.md` | Task-level progress (what's done, what's next, blockers) | Start of each session |
| `docs/research_plan.md` | Architecture, agent design, build-vs-borrow, data sources | When making design decisions |
| `docs/timeline.md` | 6-month roadmap with weekly tasks | When planning what to work on |
| `docs/project_log.md` | Session history and decisions made | When you need context on past work |
| `docs/learning_roadmap.md` | Books, courses, and educational resources | For learning |
| `README.md` | Quick setup and usage | For new setup |

---

## 11. Resuming Work (for any agent or person)

### Starting a new CoCo session:

1. Read `docs/tracker.md` — see what's done and what's next
2. Read `docs/knowledge_library.md` (this file) if you need context
3. Tell CoCo what you want to work on
4. CoCo reads relevant code, implements changes, tests them
5. At end of session: CoCo updates tracker.md, commits, pushes to GitHub

### Starting fresh (new machine or new person):

1. Follow setup in Section 2 above
2. Read this entire document
3. Read `docs/research_plan.md` for architecture
4. Check `docs/tracker.md` for current status
5. Pick a pending task and start

### If CoCo has no memory of past sessions:

Everything is in the repo. CoCo can reconstruct full context by reading:
1. This file (knowledge_library.md)
2. tracker.md
3. research_plan.md
4. The actual code in scripts/

No conversation history needed. The repo IS the memory.
