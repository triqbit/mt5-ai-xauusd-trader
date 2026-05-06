# Schema Governance and Data Validation

This document outlines the standards for data validation and schema enforcement within the MT5 AI/ML Trading Bot.

## 1. TradeSignal Schema

Trading signals are the most critical data structures in the system. To ensure technical trust and prevent catastrophic failures due to malformed data, `TradeSignal` in `src/core/schemas.py` utilizes Pydantic for strict runtime validation.

### Enforced Constraints:
- **Symbol**: Must be a valid financial instrument.
- **Direction**: Strictly limited to `1` (BUY), `-1` (SELL), or `0` (HOLD).
- **Prices**: Entry, Stop Loss, and Take Profit must be positive floats.
- **Lot Size**: Minimum size is `0.01` to prevent execution errors.
- **Confidence**: Must be between `0.0` and `1.0`.

### Price Boundary Validation (Sanity Checks):
To prevent "fat-finger" errors or model malfunctions, the following directional price checks are enforced:
- **BUY Signals**:
    - `Stop Loss` must be **below** `Entry Price`.
    - `Take Profit` must be **above** `Entry Price`.
- **SELL Signals**:
    - `Stop Loss` must be **above** `Entry Price`.
    - `Take Profit` must be **below** `Entry Price`.

Any signal that violates these boundaries will raise a `ValidationError` and will be blocked before reaching the risk engine or broker.

## 2. Validation Strategy

1. **Defensive Creation**: Objects are validated at the point of creation using Pydantic models.
2. **Standardized Enums**: `SignalDirection` IntEnum ensures consistent direction handling across models and adapters.
3. **Fail-Fast**: Invalid data triggers a `ValidationError` immediately, preventing malformed signals from propagating through the risk engine.
4. **Unified Schema**: A single source of truth for `TradeSignal` is maintained in `src/core/schemas.py` and used system-wide.

## 3. Implementation Details

The centralized schema is located at `src/core/schemas.py`. All new models or adapters generating signals MUST utilize this schema to ensure compliance with institutional safety standards.
