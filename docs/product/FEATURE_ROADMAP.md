# Strategic Feature Roadmap - April 2026

## High Priority (Next 2 Weeks)

### 1. Explainable Regime-Aware Decision Cockpit
- **Score:** 9.2/10
- **Cost:** M
- **Strategic Importance:** 9/10
- **Dependency Readiness:** 🟢 High (Core data streams active)
- **Operational Leverage:** High
- **Why:** Solves the "Black Box" problem by visualizing *why* the ensemble model is taking a position, showing regime detection (Trending/Mean-Reverting), and consolidating health metrics into a single TUI/Dashboard.

### 2. Gold-Specific Macro Sensitivity Overlays
- **Score:** 9.5/10
- **Cost:** M
- **Strategic Importance:** 10/10
- **Dependency Readiness:** 🟡 Medium (Requires YFinance/FRED integration)
- **Operational Leverage:** High
- **Why:** Provides the primary market differentiation. Integrates Real Yields, DXY correlation, and Central Bank demand into the feature vector, giving the AI a unique "institutional" edge in XAUUSD trading.

## Medium Priority (Weeks 3-4)

### 3. High-Fidelity Backtesting & Walk-Forward Validation
- **Score:** 8.0/10
- **Cost:** L
- **Strategic Importance:** 8/10
- **Dependency Readiness:** 🟢 High
- **Operational Leverage:** Medium
- **Why:** Moves beyond simple backtests to robust walk-forward optimization, ensuring the model isn't overfitted to historical Gold price action.

### 4. Institutional News & Event Sentiment Filter
- **Score:** 7.5/10
- **Cost:** M
- **Strategic Importance:** 7/10
- **Dependency Readiness:** 🔴 Low (Requires News API integration)
- **Operational Leverage:** Medium
- **Why:** Prevents the bot from entering trades during high-impact economic releases (NFP, FOMC) unless specifically trained for event volatility.

## Future Consideration

### 5. Multi-Arch Docker Deployment & Cloud Terraform
- **Score:** 6.5/10
- **Cost:** L
- **Strategic Importance:** 6/10
- **Dependency Readiness:** 🟢 High
- **Operational Leverage:** Low
- **Why:** Simplifies the "Day 1" operator experience and ensures consistent performance across ARM64 (Mac/Graviton) and AMD64 environments.

### 6. Dreamer V3 World Model Implementation
- **Score:** 7.0/10
- **Cost:** XL
- **Strategic Importance:** 7/10
- **Dependency Readiness:** 🟡 Medium (Architecture defined, implementation complex)
- **Operational Leverage:** High (Long-term)
- **Why:** Adds a predictive world model for planning, potentially increasing the Sharpe ratio by anticipating market shifts rather than just reacting.
