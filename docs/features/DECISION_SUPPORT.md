# Institutional Decision Support System

The **Decision Support System** is a critical component of the MT5 AI/ML Trading Bot, providing institutional operators with a comprehensive, structured overview of a trade signal before execution or manual review.

## Overview

The system aggregates multiple data streams into a single **Decision Packet**, ensuring that every decision is backed by explainability data, risk assessment, and historical performance context.

### Key Components

- **Signal Direction & Confidence:** Final ensemble decision and its aggregated confidence score.
- **Explainability Payload:** Detailed attribution showing which models drove the decision and the current market regime context.
- **Risk Assessment:** Consolidated view of execution filters (spread, timing, etc.) and risk gate results (daily loss limits, drawdown protection).
- **Capital Allocation:** Real-time visibility into the capital amount and risk percentage allocated to the trade.
- **Recent Performance Context:** Recent session-level performance metrics (win rates, profit factors) to identify potential overtrading or behavioral risks.

## Decision Packet Structure

The `DecisionPacket` is a typed Pydantic model containing:

- `timestamp`: Generation time (UTC).
- `symbol`: Trading symbol (e.g., XAUUSD).
- `direction`: BUY, SELL, or HOLD.
- `confidence`: Ensemble confidence score.
- `explanation`: Full `SignalExplanation` object.
- `allocation`: `AllocationResult` from the Capital Allocator.
- `recent_performance`: List of `SessionAnalysis` results.
- `is_blocked`: Boolean flag indicating if the trade was rejected by any filter.
- `block_reasons`: List of strings explaining why the trade was blocked.
- `operator_summary`: Human-readable summary for high-level review.

## Operator Interface

The system provides a high-impact terminal display using the `rich` library, featuring:

- **Color-coded status panels:** Clear visual cues for APPROVED (Green/Blue) and BLOCKED (Red) trades.
- **Formatted tables:** Clean presentation of recent session performance.
- **Plain-text fallback:** Ensures reliability in environments where `rich` is unavailable.

## Usage

Operators can generate and format a packet as follows:

```python
from src.core.decision_support import DecisionSupport

ds = DecisionSupport()
packet = ds.generate_packet(explanation, allocation, performance)
print(ds.format_for_operator(packet))
```
