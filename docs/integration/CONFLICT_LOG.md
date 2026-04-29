# Cross-Agent Conflict Log

## [2026-04-29] - Multi-Agent Architecture Drift

### 1. Async/Sync Interface Mismatch
- **Affected Files**: `src/trading/order_manager.py`, `src/trading/portfolio_manager.py`, `src/trading/mt5_connector.py`
- **Agents**: Jules01 (Connector), Jules02 (Order/Portfolio Managers)
- **Priority**: High (Systemic Failure)
- **Impact**: `OrderManager` and `PortfolioManager` use `await` on `MT5Connector` methods, but `MT5Connector` implements them as synchronous. This will cause runtime crashes on Linux/Mac where `asyncio` is expected for MetaAPI, and errors on Windows if `await` is used on non-coroutines.
- **Resolution Plan**:
    - Harmonization: Align `MT5Connector` to provide consistent sync/async interfaces or adapt Managers to the actual Connector signature.
    - Owner: Jules01 (Connector alignment) & Jules02 (Manager alignment).
    - Status: Routed to lanes.

### 2. Main Entrypoint Initialization & Logic Errors
- **Affected Files**: `main.py`
- **Agents**: Jules01
- **Priority**: High (Functional Block)
- **Impact**:
    - `RiskManager` was initialized twice, losing dependencies.
    - `run_live` loop was called twice incorrectly.
- **Resolution Plan**:
    - Fixed `main.py` to initialize `RiskManager` once and call `run_live` correctly.
    - Owner: Jules05.
    - Status: **RESOLVED** by Jules05.

### 3. Logic Fragmentation (Risk vs Portfolio vs Order Management)
- **Affected Files**: `src/trading/risk_manager.py`, `src/trading/portfolio_manager.py`, `src/trading/order_manager.py`
- **Agents**: Jules01, Jules02
- **Priority**: Medium (Architectural Debt)
- **Impact**:
    - Duplicate drawdown/exposure logic.
- **Resolution Plan**:
    - Consolidate authoritative logic in `RiskManager`.
    - Owner: Jules02.
    - Status: Pending task routing.

### 4. MetaAPI Attribute Naming Inconsistency
- **Affected Files**: `src/trading/mt5_connector.py`, `src/trading/order_manager.py`
- **Agents**: Jules01, Jules02
- **Priority**: Medium
- **Impact**: `MT5Connector` used `metaapi_connection` while `OrderManager` expected `connection`.
- **Resolution Plan**:
    - Renamed `metaapi_connection` to `connection` in `MT5Connector`.
    - Owner: Jules05.
    - Status: **RESOLVED** by Jules05.
