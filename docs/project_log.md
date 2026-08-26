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
