# Schema Governance and Data Validation

This document outlines the standards for data validation and schema enforcement within the MT5 AI/ML Trading Bot.

## 1. TradeSignal Schema

Trading signals are the most critical data structures in the system. To ensure technical trust and prevent catastrophic failures due to malformed data, `TradeSignal` in `src/core/schemas.py` utilizes Pydantic for strict runtime validation.

### Enforced Constraints:
- **Symbol**: Must be 3-20 uppercase alphanumeric characters (`^[A-Z0-9]{3,20}$`).
- **Direction**: Strictly limited to `1` (BUY), `-1` (SELL), or `0` (HOLD).
- **Prices**: Entry, Stop Loss, and Take Profit must be positive floats.
- **Lot Size**: Minimum size is `0.01` to prevent execution errors.
- **Confidence**: Must be between `0.0` and `1.0`.
- **Risk-Reward Ratio**: Minimum 1:1.5 ratio is required for all BUY/SELL signals.

### Price Boundary and Risk Validation:
To prevent "fat-finger" errors or model malfunctions, the following directional price checks are enforced:
- **BUY Signals**:
    - `Stop Loss` must be **below** `Entry Price`.
    - `Take Profit` must be **above** `Entry Price`.
- **SELL Signals**:
    - `Stop Loss` must be **above** `Entry Price`.
    - `Take Profit` must be **below** `Entry Price`.

Any signal that violates these boundaries or fails the minimum R:R check will raise a `ValidationError` and will be blocked before reaching the risk engine or broker.

### End-to-End Traceability:
- **Trace ID**: Every `TradeSignal` includes a mandatory `trace_id` field. This unique identifier is generated at the start of each trading loop and propagated through risk management and execution filters to correlate model predictions with final execution results in the audit logs.

## 2. RiskDecision Schema

To ensure technical trust in risk management, every risk assessment is formalized via the `RiskDecision` Pydantic model in `src/core/schemas.py`.

### Enforced Invariants:
- **Mandatory Rejection Reason**: If a signal is not approved (`is_approved=False`), a `blocked_by` machine-readable code MUST be provided.
- **Approval Consistency**: An approved decision (`is_approved=True`) MUST NOT have a `blocked_by` reason.
- **Audit Trace**: Every decision includes a `trace` dictionary capturing the results of all 8 risk validation layers (Circuit Breaker, Daily Loss, etc.).
- **Boolean Compatibility**: `RiskDecision` implements `__bool__` for safe integration with legacy conditional logic.

## 3. Decision Support Invariants

To maintain institutional trust, the `DecisionPacket` in `src/core/decision_support.py` enforces logical consistency between decision dimensions:
1. **Binary Executability**: If `is_executable` is True, there must be ZERO `blocking_reasons`.
2. **Status Alignment**: If `is_executable` is True, the `status_level` cannot be `BLOCKED`.
3. **Fail-Safe Integrity**: If `is_executable` is False, the `status_level` cannot be `EXECUTE`.

These invariants prevent operational surprise by ensuring that the automated decision status aligns perfectly with the underlying risk and filter results.

## 4. Validation Strategy

1. **Defensive Creation**: Objects are validated at the point of creation using Pydantic models.
2. **Standardized Enums**: `SignalDirection` IntEnum ensures consistent direction handling across models and adapters.
3. **Fail-Fast**: Invalid data triggers a `ValidationError` immediately, preventing malformed signals from propagating through the risk engine.
4. **Unified Schema**: A single source of truth for `TradeSignal` is maintained in `src/core/schemas.py` and used system-wide.

## 5. Implementation Details

The centralized schema is located at `src/core/schemas.py`. All new models or adapters generating signals MUST utilize this schema to ensure compliance with institutional safety standards.
