# Trade Signal Explainability System

## Overview
The explainability system provides institutional-grade transparency into the decision-making process of the MT5 AI/ML Trading Bot. It moves the system away from "black-box" behavior by providing structured, auditable attributions for every trade signal.

## Components
The system decomposes a trade signal into five primary dimensions:

1.  **Execution Summary:** Results from the multi-layer execution filter cascade (e.g., Spread, Momentum, Session, Volatility).
2.  **Model Attribution:** Breakdown of how individual models in the ensemble (PPO, LSTM, etc.) voted, their weights, and which models were dominant in the final decision.
3.  **Feature Contributions:** Attribution of the decision to specific feature clusters (Trend, Momentum, Volatility, Volume, Patterns) based on keyword-based mapping.
4.  **Regime Context:** Analysis of the current market state (Trending, Ranging, News Shock, etc.) and how well the signal aligns with the strategy's edge in that regime.
5.  **Risk Assessment:** Summary of risk management constraints, including R:R quality and specific reasons for rejection if the signal was blocked.

## Architecture

### `SignalExplanation` (Pydantic Model)
The root object that aggregates all attribution data. It is **immutable (frozen)** to ensure the integrity of the audit trail.

Key Methods:
- `to_report_section()`: Maps the explanation to a `StrategicConfluenceSection` for inclusion in institutional research reports.

### `SignalExplainer` (Orchestrator)
Generates the `SignalExplanation` by collecting data from across the system. It features:
- **Keyword-based Clustering:** Automatically groups raw feature impacts into logical categories.
- **Strategic Reasoning Engine:** Generates natural language summaries based on market regime and feature confluence.

## Persistence
All explained signals are persisted in the `model_signals` table via `TradeLogger`. The full structured explanation is stored as a JSON-encoded string in the `explanation` column, enabling deep post-trade analysis and regulatory auditing.

## Integration
- **Live Loop:** Every non-hold signal is automatically explained and displayed in the operator cockpit.
- **Decision Support:** Integrated into the `DecisionPacket` for real-time operator review.
- **Research Reporting:** Leveraged by `ResearchReporter` to provide strategic confluence insights.
