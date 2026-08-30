# Project Timeline: Family Quant AI

**Team:** Yaming (~1 hr/day) + Benjamin (occasional sessions)
**AI leverage:** Cortex Code (CoCo) does the heavy coding; you direct and review
**Start:** Late August 2026
**Target:** Running multi-agent research loop with paper trading

---

## Month 1 (Sep 2026): Foundation Complete + First Strategy Test

### Week 1-2: Polish the data pipeline
- [ ] Fix options fetcher (switch to alpaca-py client)
- [ ] Store computed features in DuckDB `daily_features` table
- [ ] Add regime features (VIX level, yield curve, Fed direction)
- [ ] Add fundamental features (days since earnings, EPS surprise)
- [ ] Set up Windows Task Scheduler for daily auto-updates
- **Benjamin session:** Walk through the codebase together, explain the architecture

### Week 3-4: Statistics engine + first backtest
- [ ] Build `scripts/stats_engine.py` (t-test, bootstrap, permutation, walk-forward)
- [ ] Build `scripts/backtester.py` using Alpaca Skills methodology
- [ ] Implement Strategy A: Momentum (simplest hypothesis)
- [ ] Run full backtest on momentum, review results honestly
- [ ] Document: does momentum survive out-of-sample? Record in research memory

**Month 1 deliverable:** One strategy fully backtested with proper statistics

---

## Month 2 (Oct 2026): Multiple Strategies + The Skeptic

### Week 5-6: More strategies
- [ ] Implement Strategy B: Mean Reversion (RSI + Bollinger)
- [ ] Implement Strategy C: Post-Earnings Drift
- [ ] Implement Strategy D: Macro Regime filter
- [ ] Backtest each independently
- **Benjamin session:** Review results together, discuss which look real vs noise

### Week 7-8: Build the Skeptic
- [ ] Build `scripts/skeptic.py` — automated kill criteria
- [ ] Run all strategies through the Skeptic
- [ ] Build the Gatekeeper — promotion criteria for paper trading
- [ ] Create research memory tables in DuckDB
- [ ] Record all experiment results and lessons

**Month 2 deliverable:** Multiple strategies tested, filtered, documented. Clear answer: "which (if any) survive scrutiny?"

---

## Month 3 (Nov 2026): Paper Trading + Agent Loop

### Week 9-10: Paper trading
- [ ] Build `scripts/paper_trader.py` — connects surviving strategies to Alpaca paper account
- [ ] Set up daily automated workflow (update data -> features -> signals -> orders)
- [ ] Build simple performance dashboard (notebook or script)
- [ ] Start paper trading with small positions
- **Benjamin session:** Watch the first paper trades execute together

### Week 11-12: First agent prototype
- [ ] Set up smolagents (HuggingFace) as orchestration layer
- [ ] Build Scout agent — daily anomaly scan
- [ ] Build simple Governor — weekly review of what worked/didn't
- [ ] Connect agents to DuckDB research memory
- [ ] First end-to-end agent loop: Scout finds anomaly -> Skeptic tests it -> Governor decides next step

**Month 3 deliverable:** Paper trading running daily. First agent-driven research cycle complete.

---

## Month 4 (Dec 2026): Full Multi-Agent Loop

### Week 13-14: Expand the agent team
- [ ] Build Context/Regime agent — classifies current market environment
- [ ] Build Feature Miner agent — proposes new features to test
- [ ] Improve Skeptic with stronger statistical tests
- [ ] Add execution realism (slippage sensitivity, spread analysis)
- **Benjamin session:** Review first month of paper trading results

### Week 15-16: Self-improvement loop
- [ ] Build Experimenter agent — formal experiment design and execution
- [ ] Connect Governor to research memory — learns from past failures
- [ ] First quarterly meta-review: what worked, what failed, what to investigate next
- [ ] Evaluate: do we need additional data? (Unusual Whales trial, Massive)

**Month 4 deliverable:** Full 6-agent research loop running. System proposes hypotheses, tests them, filters survivors, and learns from results.

---

## Month 5-6 (Jan-Feb 2027): Refinement + Real Edge Discovery

### Ongoing
- [ ] Monitor paper trading performance vs backtest expectations
- [ ] Let the agent system propose and test new hypotheses weekly
- [ ] Add new data sources ONLY if research identifies a specific need
- [ ] Build performance reporting (weekly summary, monthly review)
- [ ] Study reference projects (TradingAgents, quant-agent, Alpha-Agent) for architecture improvements
- [ ] Consider: is any strategy consistently profitable after costs?

**Month 5-6 deliverable:** Mature research platform. Clear understanding of what works and what doesn't. Decision point: continue paper trading, adjust strategies, or expand universe.

---

## Typical Daily Session (~1 hour)

```
Mon:  Review weekend data, check paper trading positions
Tue:  Work on current sprint task (CoCo does the coding)
Wed:  Work on current sprint task (review CoCo's output)
Thu:  Run experiments, review backtest results
Fri:  Update docs, push to GitHub, plan next week

Benjamin (weekend or evening):
- Review what changed this week
- Explore data in the notebook
- Discuss: "What did the Skeptic reject and why?"
- Learn: pick one concept to understand deeper
```

---

## How CoCo Does the Heavy Lifting

Your typical session:
```
You:    "Build the statistics engine with bootstrap and permutation tests"
CoCo:   [writes stats_engine.py, tests it, commits]

You:    "Run momentum strategy through the Skeptic"
CoCo:   [executes backtest, runs statistical tests, reports results]

You:    "The Sharpe looks too good. Test with 2x spread and remove top 5 trades"
CoCo:   [re-runs with conservative assumptions, reports]

You:    "Add this to research memory as a rejected hypothesis"
CoCo:   [stores experiment results in DuckDB]
```

You provide direction and judgment. CoCo provides speed and code quality.

---

## Key Milestones

| When | Milestone | Success Criteria |
|------|-----------|-----------------|
| End of Sep | First strategy fully backtested | Honest Sharpe, p-value, drawdown reported |
| End of Oct | Skeptic filtering working | At least 2 strategies tested, filtered, documented |
| End of Nov | Paper trading live | Daily automated pipeline producing trades |
| End of Dec | Full agent loop | 6 agents running, research memory accumulating |
| End of Feb | Edge discovery | Clear evidence of what works (or honest "nothing yet") |

---

## What "Success" Looks Like

Success is NOT: "We found a strategy that makes 50% per year."

Success IS:
1. A working research platform that can test any hypothesis rigorously
2. A growing research memory that prevents repeating mistakes
3. An honest assessment of what works and what doesn't
4. Benjamin learning coding, statistics, and financial thinking
5. A system that gets smarter over time (even if slowly)

The platform is the product. Profitable strategies are a bonus.
