# Institutional Decision Support System (DSS)

The Decision Support System is a structured operator-facing decision augmentation framework. It aggregates signal attribution, market regime, macro risk, and strategy performance into a unified, auditable decision packet before trade execution.

## Key Components

### 1. Decision Packet (`DecisionPacket`)
An immutable, typed data structure that captures the full state of a trading decision.
- **Decision Score**: A composite confidence metric (0-100).
- **Consensus**: Qualitative and quantitative ensemble agreement.
- **Market Regime**: Detected regime, confidence, and alignment.
- **Risk State**: Macroeconomic event impacts and risk-based sizing.
- **Performance Context**: Recent strategy metrics (Sharpe, Profit Factor, etc.).
- **Executive Summary**: Natural language rationale for the decision.

### 2. Scoring Formula
The `decision_score` is calculated using institutional weighting:
- **40% Model Consensus**: Weighted weighted average of ensemble votes.
- **30% Market Regime**: Detection confidence and strategy-regime alignment.
- **30% Risk & Safety**: Risk/Reward quality and macroeconomic risk multipliers.

### 3. Intelligent Sizing
The system recommends a `sizing_multiplier` (0.0 to 1.0) based on:
- **Conviction Scaling**: Non-linear scaling of the decision score `(score/100)^1.5`.
- **Status Penalties**: 50% reduction for `CAUTION` or `REVIEW` status levels.
- **Macro Volatility**: Dynamic scaling based on real-time macroeconomic event severity.

## Operational Modes

| Status | Threshold | Action |
| :--- | :--- | :--- |
| **EXECUTE** | Score >= 80 | Automated execution permitted. |
| **REVIEW** | Score >= 70 | Valid signal, but requires manual operator oversight. |
| **CAUTION** | Score < 70 | Elevated risk; reduced sizing or manual rejection recommended. |
| **BLOCKED** | N/A | Execution strictly prohibited by risk gates or macro filters. |

## Visualization
The DSS provides high-fidelity terminal dashboards using the `rich` library, including:
- Conviction Meters
- Color-coded performance KPIs
- Visual status badges and icons
- Detailed signal attribution breakdowns
