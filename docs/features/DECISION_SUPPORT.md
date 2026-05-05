# Institutional Decision Support System (DSS)

## Overview
The Institutional Decision Support System (DSS) in the MT5 AI/ML Trading Bot is designed to increase operator confidence and oversight by providing a structured, multi-dimensional view of every trading decision before execution.

Unlike simple monitoring, the DSS aggregates intelligence from across the system to provide a unified "Go/No-Go" packet that is both machine-readable for automated filters and human-readable for active review.

## Key Components

### 1. Decision Packet
The `DecisionPacket` is a structured Pydantic model that serves as the single source of truth for a trade decision. It includes:
- **Symbol & Direction:** The target asset and the intended trade direction (BUY/SELL/HOLD).
- **Consensus Level:** A qualitative measure of agreement among the ensemble models (Unanimous, Strong Majority, Mixed, etc.).
- **Execution Status:** A final "Go/No-Go" flag determined by the combined state of all filters.
- **Blocking Reasons:** A clear list of reasons if a trade is prevented from executing.

### 2. Multi-Dimensional Summary
The DSS summarizes the following dimensions:
- **Signal Attribution:** Detailed breakdown of which models drove the signal and which features contributed most (provided by `SignalExplainer`).
- **Market Regime:** Contextual awareness of the current market state (Trending, Volatile, Ranging) and its favorability.
- **Macro Risk:** Real-time awareness of macroeconomic events (CPI, FOMC, NFP) and their impact on execution safety.
- **Performance Context:** Recent strategy performance metrics (Sharpe Ratio, Win Rate, Profit Factor, Recovery Factor, and Win/Loss Ratio) to provide historical perspective.

### 3. Decision Dashboard
For human operators, the DSS generates a high-fidelity terminal dashboard using the `rich` library. This dashboard provides:
- Color-coded status and direction.
- Structured panels for market and performance overviews.
- Detailed macro intelligence including active events and impact scores.
- Full signal attribution details with model votes and feature impacts.

## Consensus Logic
The system calculates model consensus based on the weighted alignment of votes within the ensemble:
- **Unanimous:** 100% of weighted models agree on the direction.
- **Strong Majority:** At least 66% of weighted votes agree.
- **Mixed Confluence:** At least 50% of weighted votes agree.
- **Divided/Weak:** Less than 50% weighted agreement (high risk of noise).

## Technical Implementation
The system is implemented in `src/core/decision_support.py` and integrates with:
- `src/core/explainability.py` for signal details.
- `src/models/regime_detector.py` for market context.
- `src/data/event_intelligence.py` for macro risk awareness.
- `src/core/trade_logger.py` for performance history.

## Usage in Loop
When running in "Active Review" mode, the system will pause and display the Decision Dashboard for each signal, requiring operator confirmation before sending the order to MetaTrader 5.
