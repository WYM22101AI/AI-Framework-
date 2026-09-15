# Open-Source Quantitative Frameworks & Strategy Reference Guide

**Compiled for Family Quant AI Platform**  
**Date:** September 2026

This reference documents the leading open-source quant finance platforms, academic factor libraries, and modern AI trading agent architectures available on GitHub and HuggingFace, with actionable takeaways for our platform.

---

## 1. Top Open-Source Quant Frameworks (GitHub)

### 1. Microsoft Qlib & RD-Agent (48.6k ⭐)
- **Repository**: [`microsoft/qlib`](https://github.com/microsoft/qlib) & [`microsoft/RD-Agent`](https://github.com/microsoft/RD-Agent)
- **Core Focus**: AI-oriented quantitative investment platform with automated factor mining and ML modeling.
- **Key Features**:
  - Standardized feature datasets: **Alpha158** (158 price-volume factors) and **Alpha360** (360 multi-frequency factors).
  - High-performance binary data format and C++ caching layer for fast feature computation.
  - **RD-Agent**: Autonomous LLM agent framework specifically for automated factor discovery and joint model optimization.
- **Takeaways for Our Platform**:
  - We can adopt the Alpha158 formulaic expressions in `scripts/feature_engine.py` as standardized factor definitions.
  - Our 6-agent system mirrors RD-Agent's automated hypothesis-testing loop.

---

### 2. AI4Finance FinRL & FinRL-X (16.3k ⭐)
- **Repository**: [`AI4Finance-Foundation/FinRL`](https://github.com/AI4Finance-Foundation/FinRL)
- **Core Focus**: Financial Deep Reinforcement Learning (DRL) and AI-native modular trading infrastructure.
- **Key Features**:
  - Decoupled layers: Market Environments $\rightarrow$ DRL Agents (PPO, SAC, DDPG, TD3) $\rightarrow$ Execution Applications.
  - Integration with Alpaca, Yahoo Finance, and WRDS.
  - Turbulence Index & Market Environment filters.
- **Takeaways for Our Platform**:
  - Their "Turbulence Index" concept directly parallels our VIX Regime Agent (`agents/regime.py`).
  - Modular separation between data, agent decision, and execution matches our 3-layer architecture.

---

### 3. WorldQuant 101 Formulaic Alphas (Kakushadze, 2016)
- **Paper**: arXiv:1601.00991 (*"101 Formulaic Alphas"*)
- **Core Focus**: 101 explicit mathematical formulas used in real-world quant hedge funds.
- **Key Characteristics**:
  - Average holding period: 0.6 – 6.4 days (short-term mean reversion and momentum).
  - Cross-sectional ranking (`rank()`), time-series correlation (`correlation()`), decay weighting (`decay_linear()`).
  - Average pairwise correlation between alphas is low (~15.9%), making them ideal for ensemble blending.
- **Top Formulaic Alphas for Our Universe**:
  - **Alpha #6**: `-1 * correlation(open, volume, 10)` (divergence between price open and volume).
  - **Alpha #12**: `sign(delta(volume, 1)) * (-1 * delta(close, 1))` (volume price impact reversion).
  - **Alpha #53**: `-1 * delta(((close - low) - (high - close)) / (close - low + 0.0001), 9)` (intraday price pressure reversion).

---

### 4. QuantConnect LEAN (10.2k ⭐)
- **Repository**: [`QuantConnect/Lean`](https://github.com/QuantConnect/Lean)
- **Core Focus**: Institutional-grade multi-asset algorithmic trading engine in C# and Python.
- **Key Features**:
  - Fill models with realistic slippage, borrow fees, and market impact models.
  - Universe selection engines (coarse/fine fundamental screening).
- **Takeaways for Our Platform**:
  - Our `scripts/backtester.py` next-day open execution and 5 bps friction deduction aligns with LEAN's conservative fill modeling.

---

### 5. PyPortfolioOpt (4.1k ⭐)
- **Repository**: [`robertmartin8/PyPortfolioOpt`](https://github.com/robertmartin8/PyPortfolioOpt)
- **Core Focus**: Mathematical portfolio optimization in Python.
- **Key Features**:
  - **Hierarchical Risk Parity (HRP)**: Machine-learning based clustering of asset correlations to allocate weights without matrix inversion issues.
  - **Black-Litterman Allocation**: Combines market equilibrium views with quantitative strategy signals.
  - **Semivariance / CVaR Optimization**: Optimizes directly for downside protection rather than symmetric variance.
- **Takeaways for Our Platform**:
  - Use HRP or Inverse-Volatility weighting when allocating capital across approved survivor strategies in `agents/gatekeeper.py`.

---

## 2. Popular Quantitative Strategy Archetypes from Reddit / HuggingFace Communities

| Strategy Archetype | Core Hypothesis | Best Asset Class | Expected Sharpe |
|---|---|---|---|
| **1. Volatility Regime Mean Reversion** *(Our Strategy G)* | Overreaction during elevated market stress (VIX > 20) mean-reverts quickly. | High-Beta Tech (TSLA, NVDA, AMZN) | 1.2 – 1.5 |
| **2. Cross-Sectional Leader Momentum** *(Strategy L)* | Top quintile 60-day relative strength leaders outperform laggards in Risk-On regimes. | S&P 500 / Nasdaq 100 universe | 0.8 – 1.1 |
| **3. Post-Earnings Announcement Drift (PEAD)** *(Strategy N)* | Large fundamental earnings surprises cause multi-week institutional accumulation. | Mega-Cap Equities | 0.7 – 1.0 |
| **4. Volatility Risk Premium (VRP) Harvest** | Implied volatility (IV) systematically trades higher than realized volatility (RV). | S&P 500 options / Straddles | 1.1 – 1.4 |
| **5. Gamma Exposure (GEX) Pinning** | Market maker hedging flows suppress volatility near major open interest strikes. | SPY, QQQ, TSLA options | 0.9 – 1.2 |

---

## 3. Recommended Next Additions to Our Platform

1. **Alpha 101 Formula Library**: Implement a batch of Kakushadze's top 10 short-horizon formulaic alphas in `scripts/feature_engine.py`.
2. **Hierarchical Risk Parity (HRP) in Gatekeeper**: When multiple stocks pass the Skeptic, allocate weights based on inverse covariance rather than equal 25% weights.
3. **Cross-Sectional Ranking Engine**: Rank all 50 stocks every day from 1 to 50 on momentum, volatility, and volume acceleration to trade the long-short spread.
