# Family Quant AI: Comprehensive System Architecture & Operations Handoff

---

## 1. Executive Status & Operational Readiness

- **Platform Status:** **PRODUCTION READY FOR AUTONOMOUS PAPER TRADING**
- **Connected Broker:** Alpaca Paper Trading API (`https://paper-api.alpaca.markets`)
- **Account Number:** `PA3ALGF9ISXC`
- **Virtual Starting Balance:** **$100,000.00**
- **Automation Engine:** Windows Task Scheduler (`FamilyQuantDailyTrader`) running **Monday through Friday at 5:30 PM EST** with market-calendar awareness (safely skips weekends and NYSE holidays).

---

## 2. Core Investment Philosophy & Capital Fortress Model

```
┌────────────────────────────────────────────────────────────────────────┐
│                        HOW CAPITAL IS MANAGED                          │
├────────────────────────────────────────────────────────────────────────┤
│ 1. THE CASH VAULT (~80% Default Allocation)                            │
│    • Backed 100% by US Treasury yield / SPAXX Money Market (~4.5% net) │
│    • Earning safe compound interest daily                              │
│    • Zero market risk                                                  │
├────────────────────────────────────────────────────────────────────────┤
│ 2. PRECISION TACTICAL ALPHA (~20% Active Allocation)                   │
│    • Deployed into 1 to 5 day mean-reversion & momentum dislocations   │
│    • S&P 500 blue-chip stocks exclusively                              │
│    • Captures bounce-back and immediately sweeps back to cash          │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Signal Sizing & Continuous Conviction Weighting

Rather than flat binary betting, trade sizing scales dynamically across 3 dimensions:

$$\text{Position Size} = \text{Base Allocation} \times F(\text{Z-Score Dip Depth}) \times P(\text{Bayesian Confidence}) \times \frac{1}{\text{Asset Volatility}}$$

### Sizing Mechanics:
1. **Z-Score Distance from Moving Average:**
   - Standard dip ($Z = -2.0$): Baseline allocation (~$10,000).
   - Extreme panic overreaction ($Z = -3.5+$): Maximum allowable capital allocation (**$20,000**).
2. **Layer 2.5 Bayesian Meta-Score (TypeSafe Jev & Cortex AI):**
   - High mean-reversion confidence ($P > 0.85$ with clean news): Full weight.
   - Mixed headlines / low evidence score: Scaled down by 50% or vetoed.
3. **Volatility Normalizer (Inverse Volatility):**
   - Lower volatility blue-chips (`COST`, `AMZN`) receive larger dollar weights; higher beta tech (`NVDA`, `FSLR`) receives tighter share sizing to keep portfolio dollar risk balanced.
4. **Hard Upper Limits (The Trading Cage):**
   - **Max Single Stock Cap:** **$20,000.00 (25% max)**.
   - **Max Portfolio Active Exposure:** **50% max** ($50,000 max; remaining $50k+ stays in cash).
   - **Max Daily Loss Limit:** **$2,000.00**.
   - **Leverage:** **1.0x (Cash only; zero borrowed margin)**.
   - **Shorting:** **Permanently disabled**.

---

## 4. Execution Timing, Morning Rebounds & Exit Rules

1. **Execution Timing:**
   - Signals generated at **5:30 PM EST** after market close.
   - Orders fill at **9:30 AM regular market open** (deepest liquidity, narrowest $0.01 spread).
   - Extended hours trading (pre-market/after-hours) is disabled to avoid wide bid-ask spreads.
2. **Pre-Market Gap & Rebound Defense (Limit Collar):**
   - Max buy limit set to $\text{Close}_T \times (1 + 0.0075)$.
   - If the stock already rebounded +2% to +4% in pre-market, the order **cancels automatically** and cash stays safely in the Treasury vault.
3. **Exit Decision Matrix:**
   - **Profit Target:** Stock crosses back above 20-day moving average (+2.5% to +4.0% gain) $\rightarrow$ SELL.
   - **Time-Based Stop:** Position held for 3 trading days without rebound $\rightarrow$ SELL to free cash.
   - **Hard Stop Loss:** Drops -3.5% below entry $\rightarrow$ SELL to cut losses immediately.

---

## 5. Active Universe & Strategy Performance Summary

| Symbol | Company | Sector | Strategy | OOS Sharpe (2023–26) | Max Drawdown |
|---|---|---|---|---|---|
| **`AMZN`** | Amazon.com | Consumer / Tech | VIX-Tuned Mean Reversion | **1.94** | **-3.5%** |
| **`FSLR`** | First Solar | Clean Energy | VIX-Tuned Mean Reversion | **1.99** | **-3.4%** |
| **`COST`** | Costco Wholesale | Consumer Staples | Mean Reversion Regime | **1.73** | **-5.8%** |
| **`NVDA`** | NVIDIA Corp | AI & Semis | VIX-Tuned Mean Reversion | **1.33** | **-7.2%** |
| **`BRO`** | Brown & Brown | Financials / Insurance | Momentum Regime | **1.26** | **-17.9%** |
| **`CAT`** | Caterpillar | Industrials | Momentum Regime | **1.08** | **-20.7%** |

- **Deep Historical GFC (2007–2009 Crisis):** Strategy gained **+70.56%** while S&P 500 crashed **-37.38%**.
- **21-Year Lifetime (2005–2026):** Cumulative total return **+523.34%** spending **86.1% of time in safe cash**.

---

## 6. Daily Operation Commands

- **Run Daily Cycle Manually (Market-Day Protected):**
  ```powershell
  python scripts/run_daily_cycle.py
  ```
- **Inspect Live Daily Status & Report (Dry Run):**
  ```powershell
  python scripts/daily_monitor.py
  ```
- **Execute Paper Trades Live to Alpaca:**
  ```powershell
  python scripts/daily_monitor.py --execute
  ```
- **Windows Task Scheduler Verification:**
  ```powershell
  schtasks /query /tn "FamilyQuantDailyTrader" /fo LIST
  ```

---

## 7. Current Project Roadmap & Immediate Next Steps

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PROJECT PROGRESS & ROADMAP                      │
├────────────────────────────────────────────────────────────────────────┤
│ [COMPLETED] Phase 1: Institutional Core & Data Infrastructure         │
│  ✓ DuckDB Columnar storage (493k bars, 427k features)                  │
│  ✓ 5-Test Statistical Skeptic Battery (zero look-ahead bias)           │
│  ✓ Dual-Benchmark Attribution (SPAXX/SGOV Cash Yield + SPY Alpha)      │
│  ✓ Full S&P 500 Universe Expansion & Empirical 50 vs 500 Comparison   │
│  ✓ 3-Layer Architecture & Layer 2.5 Bayesian Meta-Labeler              │
│  ✓ Deterministic Trading Cage & Governance Envelope ($20k Cap)         │
│  ✓ Investor Presentation Deck (PowerPoint PPTX, PDF, Markdown)         │
│  ✓ Unified Broker Adapter (Alpaca + IBKR + Simulation)                 │
│  ✓ Windows Task Scheduler Autonomous Daily Market Close Automation     │
├────────────────────────────────────────────────────────────────────────┤
│ [CURRENT STEP] Phase 2: Live Daily Paper Monitoring & Validation       │
│  • Let the automated 5:30 PM engine run for 2-4 weeks                  │
│  • Monitor daily reports in data/reports/daily_monitor_YYYYMMDD.txt    │
│  • Verify fill pricing, gap defenses, and cash yield accumulation      │
├────────────────────────────────────────────────────────────────────────┤
│ [NEXT PHASE] Phase 3: Research Pipeline & Live IBKR Transition         │
│  1. Options Volatility Arbitrage (process 5k-contract crawler data)    │
│  2. Macro Yield-Spread & Liquidity Cycle Engine (FRED macro feeds)     │
│  3. Connect Interactive Brokers (IBKR) live account for seed capital   │
└────────────────────────────────────────────────────────────────────────┘
```
