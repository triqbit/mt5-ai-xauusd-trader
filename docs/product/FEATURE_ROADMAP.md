# 🗺️ XAUUSD AI Trading Bot: Feature Roadmap

## 🎯 Strategic Vision
To transform from a collection of ML scripts into an institutional-grade, regime-aware autonomous trading system that provides "Glass Box" transparency to its operators.

---

## 📈 Feature Opportunity Matrix

| Feature | Strategic Imp. | Cost | Readiness | Leverage | End-User Value |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Regime-Aware Execution Filters** | 9 | M | High | High | Prevents "churn" in sideways markets. |
| **Explainable Decision Cockpit** | 10 | L | Med | High | Transforms "Black Box" into "Glass Box". |
| **High-Fidelity Backtest Engine** | 8 | M | High | Med | Eliminates unrealistic backtest alpha. |
| **Dynamic Regime Detection** | 9 | M | High | High | Adapts weights to market volatility. |
| **MetaAPI Failover Activation** | 8 | S | High | Med | Critical safety for remote deployments. |
| **One-Command Training Pipeline** | 7 | S | High | Med | Simplifies system maintenance. |
| **Dreamer V3 World Model** | 9 | XL | Low | High | State-of-the-art predictive power. |

---

## 🔥 High Priority (Next 2 Weeks)

### 1. Regime-Aware Execution Filters
- **Score:** 9/10 | **Cost:** M
- **Rationale:** The current 6-layer filter is static. Adding a regime-aware layer (Volatility/Trend/Range) will significantly reduce drawdowns in unfavorable market conditions.
- **Dependency:** Ready. Can utilize existing TA-Lib indicators.

### 2. High-Fidelity Backtest Engine
- **Score:** 8/10 | **Cost:** M
- **Rationale:** Core validation currently lacks realistic slippage, variable spread, and commission modeling. This is a critical safety gap before live deployment.
- **Dependency:** Ready. Requires expansion of `tests/integration_runner.py`.

### 3. One-Command Training Pipeline
- **Score:** 7/10 | **Cost:** S
- **Rationale:** Currently, training is fragmented across scripts. A unified `python main.py --mode train` command ensures consistent data preprocessing and model versioning.
- **Dependency:** Ready. Architecture exists in `main.py`.

---

## 🏗️ Medium Priority (Weeks 3-4)

### 4. Explainable Decision Cockpit (Dashboard)
- **Score:** 10/10 | **Cost:** L
- **Rationale:** The #1 differentiator for institutional use. Uses SHAP or Integrated Gradients to show *why* the ensemble chose a specific direction, visualized in a Dash/Streamlit web UI.
- **Dependency:** Moderate. Needs integration of SHAP/LIME into `src/models/ensemble.py`.

### 5. Dynamic Regime Detection Module
- **Score:** 9/10 | **Cost:** M
- **Rationale:** Uses HMM (Hidden Markov Models) or unsupervised clustering to classify the market state (Bullish Volatile, Bearish Quiet, etc.) and dynamically adjust Ensemble weights.
- **Dependency:** Ready. Scikit-learn can be added to dependencies.

### 6. MetaAPI Failover Activation
- **Score:** 8/10 | **Cost:** S
- **Rationale:** Hardens the system against local infrastructure failure. If the native MT5 connector loses heartbeat, the system should hot-swap to MetaAPI cloud execution.
- **Dependency:** High. `src/trading/mt5_connector.py` already has the scaffolding.

---

## 🔭 Future Consideration

### 7. Dreamer V3 Latent Space Model
- **Score:** 9/10 | **Cost:** XL
- **Rationale:** Moving beyond PPO to World Models. Predictive power is superior but implementation complexity and compute requirements are high.

### 8. Multi-Symbol Risk Parity
- **Score:** 7/10 | **Cost:** M
- **Rationale:** Expanding the "All-Weather" logic from `src/trading/risk_manager.py` to actively trade uncorrelated pairs (USDCHF, JPY) to hedge XAUUSD exposure.

### 9. Sentiment & Macro Event Intelligence
- **Score:** 6/10 | **Cost:** L
- **Rationale:** Integrating economic calendar feeds to automatically flatten positions or widen stops before high-impact news (NFP, FOMC).

---

## ✅ Acceptance Criteria for New Features
Every feature added must satisfy:
1. **Functional:** Pass the relevant backtest/integration test.
2. **Safety:** No increase in max drawdown during stress-test scenarios.
3. **Observability:** Must log its state and decisions to `TradeLogger`.
4. **Release:** Must include documentation and a runbook update.
