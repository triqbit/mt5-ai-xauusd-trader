# Institutional Decision Support System (DSS)

## Overview
The Institutional Decision Support System (DSS) in the MT5 AI/ML Trading Bot is designed to increase operator confidence and oversight by providing a structured, multi-dimensional view of every trading decision before execution.

Unlike simple monitoring, the DSS aggregates intelligence from across the system to provide a unified "Go/No-Go" packet that is both machine-readable for automated filters and human-readable for active review.

## Key Components

### 1. Decision Packet
The `DecisionPacket` is a structured Pydantic model that serves as the single source of truth for a trade decision. It includes:
- **Symbol & Direction:** The target asset and the intended trade direction (BUY/SELL/HOLD).
- **Consensus Level:** A qualitative measure of agreement among the ensemble models (Unanimous, Strong Majority, Mixed, etc.).
- **Decision Status:** Augmented status level (`EXECUTE`, `CAUTION`, `BLOCKED`) derived from overall decision quality.
- **Decision Score:** A composite score (0-100) aggregating multiple intelligence dimensions. The score is strictly clamped between 0 and 100 for numerical stability.
- **Sizing Multiplier:** A recommended scaling factor (0.0-1.0) for position sizing based on risk and confidence.
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
- Semantic icons and emojis (📈/📉, ✅/⚠️/🛑, 💎/💪) for rapid scannability and accessibility.
- Color-coded status and direction.
- **Institutional Metric Highlighting:** Sharpe Ratio, Profit Factor, Recovery Factor, Win Rate, and Win/Loss Ratio are color-coded (Green/Yellow/Red) based on institutional health targets (e.g., Green for Win Rate >= 55%).
- Structured panels with descriptive icons for market and performance overviews.
- **High Conviction Badge:** A `[HIGH CONVICTION] 💎` visual indicator for signals with a decision score of 90 or higher.
- **Conviction Meter:** A visual progress bar showing the decision score conviction at a glance.
- **Execution Blocked Panel:** A dedicated, high-visibility warning panel for blocked trades to ensure critical rejection reasons are not missed.
- Detailed macro intelligence including active events and impact scores.
- Full signal attribution details with model votes and feature impacts.

## Augmented Decision Logic

### Decision Score (0-100)
The DSS calculates a weighted composite score to quantify the quality of a trade setup:
- **Ensemble Consensus (40%):** Strength of agreement among models.
- **Regime Confidence (30%):** Reliability of the detected market regime.
- **Risk & Safety (30%):** Decomposed into Risk:Reward quality (20%, normalized against a 3.0 target) and Macro Safety (10%).

### Sizing Recommendation
The `sizing_multiplier` provides dynamic position sizing advice:
- **EXECUTE Status:** Sizing is scaled non-linearly based on the decision score ($score^{1.5}$).
- **CAUTION Status:** A 50% penalty is applied to the base multiplier to reduce exposure in marginal setups.
- **BLOCKED Status:** Multiplier is forced to 0.0.
- **Macro Risk:** Final sizing is always adjusted by the `macro_risk.risk_multiplier`.

### Consensus Logic
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

This system ensures that every trade is backed by verifiable intelligence across multiple analytical domains.
