# Institutional Decision Support System (DSS)

## Overview
The Decision Support System (DSS) is a core component of the XAUUSD trading platform designed to provide operators with a structured, auditable, and high-confidence "decision packet" before any trade execution. It augments the raw signal generation with market regime awareness, macro-economic safety checks, and historical performance context.

## Key Components

### DecisionPacket
A typed, immutable Pydantic model that aggregates:
- **Signal Direction:** Buy, Sell, or Hold.
- **Consensus Score (0-40):** Weighted agreement among the ensemble models.
- **Regime Score (0-30):** Alignment with the current market state and volatility.
- **Risk Score (0-30):** Evaluation of Risk/Reward quality and macro-economic safety.
- **Decision Score (0-100):** Composite score determining the execution status.
- **Status Level:** EXECUTE, REVIEW, CAUTION, or BLOCKED.
- **Executive Summary:** Natural language rationale for the decision.

### DecisionSupportSystem
The orchestrator responsible for assembling packets and applying the decision augmentation logic:
- **EXECUTE (Score >= 80):** High-confidence signal passing all institutional guardrails.
- **REVIEW (60 <= Score < 80):** Valid signal requiring manual oversight.
- **CAUTION (Score < 60):** Elevated operational risk; manual review and reduced sizing recommended.
- **BLOCKED:** Signal rejected by risk management or macro intelligence.

## Operator Interface
The DSS provides a high-fidelity terminal dashboard using the `rich` library. This dashboard includes:
- **Consensus Indicators:** Visual representation of model agreement.
- **Conviction Meters:** Color-coded progress bars for decision scores.
- **Strategic Insights:** Analysis of regime alignment and performance context (Sharpe Ratio, Win Rate).
- **Macro Alerts:** Real-time macroeconomic event tracking.

## Usage
```python
from src.core.decision_support import DecisionSupportSystem

dss = DecisionSupportSystem()
packet = dss.assemble_packet(
    symbol="XAUUSD",
    explanation=signal_explanation,
    regime_info=market_regime,
    macro_risk=risk_status,
    performance_metrics=account_metrics
)

# Display to operator
dss.format_for_operator(packet)
```

## Safety and Validation
- **Immutability:** All packets are frozen to ensure an unalterable audit trail.
- **Range Constraints:** Strict Pydantic validation on all scores and multipliers.
- **Clamping:** Automatic clamping of sub-scores to prevent validation failures during extreme market conditions.
