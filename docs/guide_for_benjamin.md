# Family Quant AI: Technical Guide for Benjamin

**Written by: Dad + CoCo (AI coding assistant)**
**Last updated: September 2026**

Hey Benjamin -- this document explains everything we've built so far, how it works, and why we made each decision. Read it start to finish the first time, then use it as a reference.

---

## What We're Building

We're building a system that:
1. Downloads financial data every day (stock prices, economic indicators, earnings, news)
2. Computes "features" -- numbers that describe what's happening in the market
3. Generates trading ideas ("hypotheses")
4. Tests each idea with real statistics to see if it's actually good or just luck
5. Only trades ideas that survive rigorous testing
6. Learns from its mistakes over time

Think of it like a science lab for the stock market. We're not guessing -- we're running experiments.

---

## The Big Idea (Most Important Section)

Most people who try to trade with AI do this:

```
"AI, should I buy TSLA?" --> AI says "yes" --> they buy
```

That's terrible. The AI is just pattern-matching on vibes.

What WE do instead:

```
AI finds something unusual ("NVDA dropped 10% but nothing bad happened")
    |
    v
We turn that into a testable hypothesis
    |
    v
We test it on 5+ years of historical data
    |
    v
We run 5 statistical tests trying to PROVE IT DOESN'T WORK
    |
    v
If we can't kill it --> maybe it's real --> paper trade it
```

The key insight: **our edge isn't "AI finds patterns." Our edge is: AI finds hypotheses, then deterministic math tries to destroy them. Only the survivors get traded.**

---

## How the Code Works

### The Pipeline (runs daily after market close)

```
python daily_pipeline.py

Step 1: Download new data
  - Stock prices from Alpaca (16 tickers)
  - Macro data from FRED (CPI, unemployment, interest rates, VIX)
  - Earnings from Alpha Vantage (quarterly EPS reports)
  - Company financials from SEC (revenue, income)
  - News headlines from Alpaca

Step 2: Compute features
  - Calculate 19 numbers per stock per day
  - These numbers describe "what state is this stock in?"

Step 3: Generate signals
  - Check: is any stock in a condition that historically led to profits?

Step 4: Paper trade
  - If a signal fires: show what we'd buy/sell (dry run)
  - With --execute flag: actually submit orders to Alpaca paper account
```

### Key Files

| File | What it does |
|------|-------------|
| `config.py` | All settings (tickers, API keys, database path) |
| `daily_pipeline.py` | Runs the full pipeline end-to-end |
| `update_market_data.py` | Downloads data from all 5 sources |
| `scripts/feature_engine.py` | Computes the 19 features |
| `scripts/signal_generator.py` | Defines trading strategies |
| `scripts/stats_engine.py` | Statistical tests (the "Skeptic") |
| `scripts/backtester.py` | Tests strategies on historical data |
| `scripts/paper_trader.py` | Submits orders to Alpaca |

---

## The 19 Features (What We Measure Every Day)

### Technical Features (from stock prices)

| Feature | What it means | Example |
|---------|--------------|---------|
| `return_1d` | How much the stock moved today | +2.3% |
| `return_5d` | How much it moved in 5 days | -1.5% |
| `return_20d` | 20-day momentum | +8.2% |
| `return_60d` | 60-day trend | +15.1% |
| `volatility_20d` | How wild the price swings are (annualized) | 45% |
| `distance_from_ma50` | Is price above or below its 50-day average? | +3.2% above |
| `distance_from_ma200` | Same for 200-day average | -5.1% below |
| `rsi_14` | RSI = Relative Strength Index (0-100). Below 30 = "oversold", above 70 = "overbought" | 28 (oversold) |
| `relative_volume` | Today's volume vs normal. 2.0 = twice normal | 1.8x |
| `bollinger_position` | Where price sits in its normal range. Below -1 = unusually low | -1.2 |
| `relative_strength_vs_spy` | Is this stock beating or losing to the market? | +0.05 (beating) |

### Regime Features (from economic data)

| Feature | What it means |
|---------|--------------|
| `vix` | The "fear index." Below 15 = calm, above 25 = scared, above 35 = panic |
| `vix_change_5d` | Is fear rising or falling? |
| `fed_funds` | The interest rate the Federal Reserve sets |
| `treasury_10y` | 10-year government bond yield |

### Fundamental Features (from earnings)

| Feature | What it means |
|---------|--------------|
| `days_since_earnings` | How many days since the company reported earnings |
| `last_eps_surprise` | Did earnings beat or miss expectations? +5% = beat by 5% |
| `earnings_within_7d` | Is an earnings report coming in the next week? |

---

## The Strategies We Tested

### What Failed (and why that's valuable)

| Strategy | Idea | Result | Lesson |
|----------|------|--------|--------|
| **Momentum** | Buy stocks going up, sell stocks going down | FAIL on all stocks | This is the most basic strategy. Everyone knows it. It's been traded to death. |
| **Mean Reversion** | Buy oversold stocks (RSI < 30) | FAIL on most stocks | Works slightly but not enough to cover trading costs |
| **Earnings Drift** | Buy after positive earnings surprise | No signal | Our earnings data was incomplete |
| **Momentum + VIX filter** | Only trade momentum when VIX is low | Still FAIL | The underlying momentum signal is just too weak |

**Why 0 survivors is okay:** If basic textbook strategies still worked easily, everyone would be rich. The fact that they fail confirms our testing system is honest.

### What Survived: VIX-Conditional Mean Reversion

```
WHEN:   VIX > 20 (market is scared)
AND:    RSI < 35 (stock is oversold)
AND:    Bollinger < -0.6 (price is unusually low)
THEN:   BUY

WHEN:   VIX > 20
AND:    RSI > 65 (stock is overbought)
AND:    Bollinger > 0.6
THEN:   SELL SHORT
```

**In plain English:** When the overall market is fearful and a specific stock has been beaten down too far, buy it. The bounce tends to be sharp and reliable.

**Results after testing on 15 stocks:**

| Stock | Annual Return | Sharpe Ratio | Passed Skeptic? |
|-------|-------------|-------------|----------------|
| AMZN | +10.8% | 1.46 | YES (4/5 tests) |
| NVDA | +9.6% | 1.02 | YES (4/5 tests) |
| AMD | +5.0% | 0.62 | No (1/5) |
| TSLA | +4.6% | 0.57 | No (1/5) |
| MSFT | +2.4% | 0.15 | No (1/5) |

**Why it works better on tech stocks:** High-beta stocks (AMZN, NVDA, TSLA) overshoot more during selloffs, so the bounce is bigger. Defensive stocks (WMT, JNJ) don't drop as much, so there's less bounce to capture.

---

## The Skeptic: How We Test If a Strategy Is Real

This is the most important part of the whole system. The Skeptic runs 5 tests:

### Test 1: t-test
**Question:** "Is the average return statistically different from zero?"
**How:** Standard statistical test. If p-value < 0.05, it passes.
**Why it matters:** A strategy might look profitable but that could be pure luck.

### Test 2: Bootstrap Confidence Interval
**Question:** "If we resample the data 10,000 times, does zero fall inside the confidence interval?"
**How:** Randomly pick returns with replacement, compute the mean 10,000 times, check the range.
**Why it matters:** More robust than a single t-test.

### Test 3: Permutation Test
**Question:** "If we randomly shuffled which days we traded, would we do just as well?"
**How:** Shuffle the signal 5,000 times, compare each shuffled result to the real one.
**Why it matters:** If random trading does just as well, our signal is meaningless.

### Test 4: Walk-Forward Test
**Question:** "Does it work consistently across different time periods?"
**How:** Split the data into 5 sequential chunks, test each separately.
**Why it matters:** A strategy that only worked in 2021 but not 2023-2026 is probably a fluke.

### Test 5: Economic Significance
**Question:** "Does the edge survive after trading costs?"
**How:** Subtract estimated transaction costs (spreads, slippage) from returns.
**Why it matters:** A strategy that makes 0.05% per trade but costs 0.04% per trade is useless.

**Verdict:** PASS = 4-5 tests passed. WEAK = 3. FAIL = 0-2.

---

## Key Concepts to Understand

### Sharpe Ratio
The most important number in quantitative finance. It measures **return per unit of risk.**

```
Sharpe = (average return) / (standard deviation of returns) * sqrt(252)
```

| Sharpe | Meaning |
|--------|---------|
| < 0 | Losing money |
| 0 - 0.5 | Weak |
| 0.5 - 1.0 | Decent |
| 1.0 - 2.0 | Good |
| > 2.0 | Suspicious (probably overfit) |

Our AMZN strategy has Sharpe 1.46 -- that's genuinely good.

### Overfitting
The #1 danger in quant finance. It means your strategy memorized the past instead of finding a real pattern.

**Example of overfitting:**
```
"Buy TSLA every third Tuesday in months starting with J when the moon is waning"
Backtest: +200% return!
Reality: Pure coincidence.
```

**How we avoid it:**
- Split data: train on 2016-2022, test on 2023-2026
- If in-sample looks great but out-of-sample looks bad = overfitting
- Our system warns: "IS Sharpe >> OOS Sharpe"

### Adjusted Prices
Stock prices in our database are "adjusted" for splits and dividends.

Tesla split 5:1 in August 2020 (a $2,000 share became five $400 shares) and 3:1 in August 2022. Our data retroactively divides ALL historical prices by 15 so the chart looks smooth and returns can be calculated correctly.

### Annualized Returns
To compare a stock's return to a CD or savings account, use **365 calendar days**:

```
annualized = (1 + total_return) ^ (365 / calendar_days) - 1
```

NOT 252 trading days. That's only for annualizing volatility (risk).

---

## The Database

Everything lives in a single file: `data/market_data.duckdb`

DuckDB is like SQLite but optimized for analytics. You can query it with SQL:

```python
import duckdb
conn = duckdb.connect("data/market_data.duckdb", read_only=True)

# See all tables
print(conn.execute("SHOW TABLES").fetchall())

# Get TSLA's last 5 days
print(conn.execute("""
    SELECT timestamp::DATE, close
    FROM daily_bars
    WHERE symbol = 'TSLA'
    ORDER BY timestamp DESC
    LIMIT 5
""").fetchdf())

# See today's features
print(conn.execute("""
    SELECT symbol, rsi_14, vix, bollinger_position
    FROM daily_features
    WHERE date = (SELECT MAX(date) FROM daily_features)
""").fetchdf())

conn.close()
```

### Tables

| Table | Rows | What's in it |
|-------|------|-------------|
| daily_bars | 24,556 | Stock prices (open, high, low, close, volume) for 16 tickers |
| macro_releases | 29,572 | Economic data (CPI, unemployment, interest rates, VIX) |
| earnings | 296 | Quarterly earnings per share with analyst estimates |
| fundamentals | 214 | Revenue, income, assets from SEC filings |
| news | 55 | Recent news headlines |
| daily_features | 20,034 | 19 computed features per stock per day |
| research_experiments | 9+ | Records of every strategy we've tested |
| trade_log | varies | Paper trading order history |

---

## The 6-Agent Architecture (Coming Next)

We're building towards a team of AI agents that do different jobs:

| Agent | Job | LLM or Code? |
|-------|-----|-------------|
| **Scout** | "What looks unusual today?" | AI |
| **Context/Regime** | "What kind of market are we in?" | Code |
| **Feature Miner** | "What new patterns should we test?" | AI |
| **Skeptic** | "Prove this isn't noise." | **Strictly code** |
| **Experimenter** | "Design and run the test." | **Strictly code** |
| **Governor** | "What should we investigate next?" | AI |

**Critical rule:** AI agents NEVER compute statistics. They request tests; Python executes them. This prevents the AI from "convincing itself" something works.

---

## How to Run Everything

```bash
# Activate the environment
cd C:\Users\Yaming\family-quant-ai      # or wherever you cloned it
venv\Scripts\activate                     # Windows
source venv/bin/activate                  # Mac

# Run the daily pipeline (dry run)
python daily_pipeline.py

# Run it for real (submits orders to paper account)
python daily_pipeline.py --execute

# Just update data
python update_market_data.py

# Just compute features
python scripts/feature_engine.py

# Test a strategy
python scripts/signal_generator.py

# Run all strategies on all stocks
python scripts/run_all_strategies.py

# Explore in notebook
jupyter notebook notebooks/exploration.ipynb
```

---

## Things To Try (Homework Challenges)

### Easy
1. Open `notebooks/exploration.ipynb` and run all cells. Look at the charts.
2. Query the database: what was NVDA's RSI on the day it dropped the most?
3. How many days in the last year was VIX above 20?

### Medium
4. Add a new feature to `feature_engine.py` (e.g., 10-day average volume)
5. Create a new strategy in `signal_generator.py` (e.g., buy when VIX drops below 15 after being above 25)
6. Run your strategy through `run_strategy_test()` and see the Skeptic verdict

### Hard
7. Add a new stock ticker to `config.py`, fetch data, compute features, test the mean reversion strategy on it
8. Modify the parameter sweep (`scripts/param_sweep.py`) to test a new parameter combination
9. Write a query that finds all dates where AMZN was oversold AND VIX > 20, and show what happened the next day

---

## Where To Learn More

| Topic | Resource |
|-------|----------|
| Python basics | Python for Everybody (free online) |
| Pandas/DataFrames | 10 Minutes to Pandas (official tutorial) |
| SQL | Mode Analytics SQL Tutorial (free) |
| Statistics | Khan Academy Statistics and Probability |
| Stock market | "A Random Walk Down Wall Street" by Burton Malkiel |
| Machine learning | "Hands-On ML" by Aurelien Geron |
| AI agents | HuggingFace Agents Course (free) |

See `docs/learning_roadmap.md` for the full reading list.

---

## One Last Thing

This project isn't about getting rich from trading. It's about learning:
- How to write code that solves real problems
- How to think scientifically (hypothesis -> test -> learn)
- How financial markets work
- How statistics separates signal from noise
- How AI can assist research (not replace thinking)

The platform is the product. The learning is the real return.
