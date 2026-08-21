# Family Quant AI

A parent-son project to collect market data, learn AI/ML, and build financial research tools.

## What It Does

- Fetches daily stock bar data (OHLCV) from Alpaca Markets API
- Stores it in a local DuckDB database for fast analytical queries
- Supports multiple tickers: TSLA, AAPL, NVDA, SPY
- Incremental updates (only fetches data newer than what's already stored)

## Project Structure

```
family-quant-ai/
├── config.py               # Central settings (tickers, DB path, API config)
├── update_market_data.py   # Main script - run this to fetch & store data
├── requirements.txt        # Python dependencies
├── .env                    # Your API keys (not in git)
├── .env.example            # Template for .env
├── scripts/
│   ├── market_fetcher.py   # Alpaca API fetch logic
│   ├── storage.py          # DuckDB read/write operations
│   └── run_update.bat      # Windows batch file for scheduling
├── data/
│   └── market_data.duckdb  # Local database (not in git)
├── docs/
│   └── learning_roadmap.md # Learning phases and resources
├── notebooks/
│   └── exploration.ipynb   # For analysis experiments
└── archive/                # Old experimental scripts (reference only)
```

## Setup

1. **Clone the repo:**
   ```
   git clone https://github.com/WYM22101AI/AI-Framework-.git family-quant-ai
   cd family-quant-ai
   ```

2. **Create virtual environment:**
   ```
   python -m venv venv
   venv\Scripts\activate      # Windows
   # source venv/bin/activate  # Mac/Linux
   ```

3. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

4. **Set up API keys:**
   - Copy `.env.example` to `.env`
   - Add your Alpaca paper trading keys (get them at https://app.alpaca.markets)

## Usage

### Manual update
```
python update_market_data.py
```

### Scheduled updates (Windows Task Scheduler)
1. Open Task Scheduler
2. Create Basic Task > "Market Data Update"
3. Trigger: Daily at 5:00 PM (after market close)
4. Action: Start a program
   - Program: `C:\Users\Yaming\family-quant-ai\scripts\run_update.bat`
5. Done

### Query the data
```python
import duckdb
conn = duckdb.connect("data/market_data.duckdb")
df = conn.execute("SELECT * FROM daily_bars WHERE symbol = 'TSLA' ORDER BY timestamp DESC LIMIT 10").fetchdf()
print(df)
conn.close()
```

## Data Feed

Using Alpaca's free IEX feed. Data is split and dividend adjusted (`adjustment="all"`).

## Next Steps

- [ ] Add technical indicators (moving averages, RSI, Bollinger Bands)
- [ ] Build analysis notebooks for visualization
- [ ] News sentiment integration
- [ ] Regime detection (trending vs sideways markets)
- [ ] Paper trading agent
