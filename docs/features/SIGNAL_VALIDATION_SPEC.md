# Signal Validation Specification

## Overview
This document defines the technical standards and validation logic for trading signals in the MT5 AI Trading Bot. All signals must conform to this schema before being considered for risk approval or execution.

## TradeSignal Schema
The `TradeSignal` model (implemented via Pydantic) enforces the following constraints:

| Field | Type | Validation | Description |
|-------|------|------------|-------------|
| `symbol` | `str` | 3-20 chars | Trading symbol (e.g., XAUUSD) |
| `direction` | `SignalDirection` | BUY or SELL | HOLD is strictly prohibited in the final signal object |
| `entry_price` | `float` | > 0 | Expected entry price |
| `stop_loss` | `float` | > 0 | Hard stop loss price |
| `take_profit` | `float` | > 0 | Hard take profit price |
| `lot_size` | `float` | > 0 | Position size in lots |
| `algorithm` | `str` | Non-empty | ID of the source algorithm |
| `confidence` | `float` | 0.0 - 1.0 | Model confidence score |
| `timestamp` | `datetime` | UTC | Time of signal generation |

## Cross-Field Validation Rules
To prevent logical errors in execution, the following rules are enforced:

### BUY Signals
- **Stop Loss**: Must be strictly below the entry price.
- **Take Profit**: Must be strictly above the entry price.

### SELL Signals
- **Stop Loss**: Must be strictly above the entry price.
- **Take Profit**: Must be strictly below the entry price.

## Implementation Details
- **Location**: `src/trading/risk_manager.py`
- **Enforcement**: Validation occurs at instantiation time. Any attempt to create an invalid `TradeSignal` will raise a `pydantic.ValidationError`.
- **Integration**: The `RiskManager.approve()` method receives a pre-validated `TradeSignal` and performs further risk-layer checks (drawdown, daily loss, etc.).
