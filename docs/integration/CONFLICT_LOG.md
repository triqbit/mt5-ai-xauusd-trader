# Cross-Agent Conflict Log

## [2026-04-19] - Harmonization of `main.py` and `MT5Connector`

### Conflicts Detected

1.  **Interface Mismatch / Sequencing Error**: `MT5Connector.initialize()` vs `MT5Connector.connect()`.
    - **Affected Files**: `src/trading/mt5_connector.py`, `main.py`
    - **Agents**: Jules01 (Core Architecture), Jules02 (Hardening)
    - **Description**: Both methods exist and perform the same action. `main.py` uses both interchangeably.
    - **Priority**: Medium
    - **Resolution**: Harmonize to use `connect()` as the primary method, keeping `initialize()` as a deprecated alias for backward compatibility.

2.  **Duplicated Logic / Interface Mismatch**: `RiskManager` initialization and usage in `main.py`.
    - **Affected Files**: `main.py`, `src/trading/risk_manager.py`
    - **Agents**: Jules01, Jules02
    - **Description**: `RiskManager` is initialized twice in `main.py`. Once with `trade_logger` and once with `monitor`. The second initialization overwrites the first, losing the `trade_logger` reference.
    - **Priority**: High
    - **Resolution**: Consolidate into a single initialization.

3.  **Broken Assumptions / Sequencing Errors**: `run_live` calls in `main.py`.
    - **Affected Files**: `main.py`
    - **Agents**: Jules01, Jules03
    - **Description**: `run_live` is called twice in a row. The first call will enter an infinite loop, making the second call unreachable. The signatures also differ in the calls.
    - **Priority**: High
    - **Resolution**: Consolidate into a single `run_live` call with all necessary components.

4.  **Naming Inconsistency**: `get_rates()` vs `get_ohlcv()` in `MT5Connector`.
    - **Affected Files**: `src/trading/mt5_connector.py`, `main.py`
    - **Agents**: Jules01, Jules04
    - **Description**: `MT5Connector` has both `get_rates()` and `get_ohlcv()`.
    - **Priority**: Low
    - **Resolution**: Harmonize to `get_ohlcv()` as it's more descriptive for ML workflows.

### Resolution Plan

- **Harmonization Approach**: Refactor `main.py` to correctly initialize and use components. Refactor `MT5Connector` to provide a consistent interface.
- **Owner**: Jules05 (Integration)
- **Required Changes**:
    - Update `src/trading/mt5_connector.py` to mark `initialize` and `get_rates` as deprecated (or just keep them as aliases but prefer others).
    - Update `main.py` to fix double initialization and double `run_live` calls.
- **Testing Requirements**:
    - Verify `main.py` starts correctly (smoke test).
    - Run unit tests for `RiskManager` and `MT5Connector`.
