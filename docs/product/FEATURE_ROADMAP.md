# 🗺️ MT5 AI/ML XAUUSD Trader: Product Roadmap

This roadmap outlines the strategic evolution of the Jules05-governed trading system, focusing on institutional-grade intelligence, safety, and XAUUSD market differentiation.

## 📊 Repository Maturity Assessment

| Category | Status | Analysis |
| :--- | :--- | :--- |
| **Product Capability** | 🟢 Mature | Core execution, multi-algorithm support, and risk management are functional. |
| **Usability** | 🟡 Emerging | CLI-driven; lacks real-time visualization and simplified operator dashboards. |
| **Safety** | 🟢 Mature | 6-layer risk filter and circuit breakers provide strong protection. |
| **Intelligence** | 🟡 Emerging | Ensemble uses simple weighting; lacks regime-awareness and macro-context. |
| **Differentiation** | 🟡 Emerging | Strong foundation, but needs more XAUUSD-specific alpha (DXY, Real Rates). |

---

## 🚀 Feature Opportunities

### 1. Adaptive Market Regime Detector
- **Description:** A specialized model (HMM or GMM) to classify the market into Trending (Bull/Bear), Ranging (Low/High Vol), or Chaotic.
- **Score:** 9/10 | **Cost:** M | **Ready:** Yes | **Leverage:** High
- **Why:** Prevents DRL agents from "bleeding" in ranging markets by dynamically adjusting risk or pausing execution.

### 2. Macro-Economic Event Filter (News Integration)
- **Description:** Integration of an economic calendar (e.g., ForexFactory API) to automatically halt trading 15m before/after high-impact XAUUSD news (CPI, NFP, FOMC).
- **Score:** 8/10 | **Cost:** M | **Ready:** Yes | **Leverage:** High
- **Why:** Protects against "Black Swan" slippage and extreme volatility that technical models often fail to predict.

### 3. XAUUSD-DXY Correlation Modeler
- **Description:** Incorporate real-time US Dollar Index (DXY) features into the observation space to exploit the inverse correlation between Gold and the Greenback.
- **Score:** 8/10 | **Cost:** S | **Ready:** Yes | **Leverage:** Med
- **Why:** Provides the model with fundamental "Gravity" context specific to XAUUSD trading.

### 4. SHAP/LIME Explainability Engine
- **Description:** A tool to generate feature importance plots for every trade signal, explaining *why* the ensemble decided to go long or short.
- **Score:** 7/10 | **Cost:** L | **Ready:** Yes | **Leverage:** Med
- **Why:** Critical for operator trust and debugging model drift during unexpected market behavior.

---

## 🗓️ Prioritized Roadmap

## High Priority (Next 2 Weeks)
- **Adaptive Market Regime Detector** — Score: 9/10 | Cost: M | Why: Immediate impact on reducing drawdown by filtering out "chop" phases where RL models underperform.
- **Macro-Economic Event Filter** — Score: 8/10 | Cost: M | Why: Prevents catastrophic losses during major news releases (CPI/NFP) which are the primary failure points for retail bots.

## Medium Priority (Weeks 3-4)
- **XAUUSD-DXY Correlation Modeler** — Score: 8/10 | Cost: S | Why: Low-cost implementation that provides significant alpha by tracking the primary driver of Gold prices.
- **Dynamic Ensemble Re-weighting** — Score: 7/10 | Cost: M | Why: Moves beyond simple averaging to use performance-based attention for model weighting.

## Future Consideration
- **Institutional Order Flow Analysis** — Score: 6/10 | Cost: XL | Why: High alpha potential but requires expensive data feeds (Level 2/LMAX) and complex engineering.
- **Multi-Agent Hedging (XAU/USD vs XAU/EUR)** — Score: 5/10 | Cost: L | Why: Advanced portfolio strategy to hedge currency risk while maintaining gold exposure.

---

## 🧠 Jules05 Strategic Focus
Jules05 will prioritize **Safety and Differentiation** in the short term. The goal is to make this bot not just "another RL trader," but an **XAUUSD Specialist** that respects macro-economic boundaries and market regimes.
