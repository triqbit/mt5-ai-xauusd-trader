# Multi-Agent Task Routing

Corrective tasks derived from Jules05 harmonization audit.

## Task: ⚡ Jules01 — Connector Interface Alignment
- **Problem**: `MT5Connector` methods are sync, but Linux/Mac environments using MetaAPI require async.
- **Requirement**:
    - Update `MT5Connector` to provide async-ready methods for `get_rates`, `get_tick`, and `place_order` when using MetaAPI.
    - Implement the missing `place_order` logic for MetaAPI.
- **Files**: `src/trading/mt5_connector.py`

## Task: 🛡️ Jules02 — Manager Interface & Logic Standardization
- **Problem**: `OrderManager` and `PortfolioManager` assume `MT5Connector` methods are async.
- **Requirement**:
    - Standardize `OrderManager.execute_trade` and `PortfolioManager` methods to handle both sync (Desktop) and async (MetaAPI) paths correctly.
    - Consolidate drawdown and exposure calculation into `RiskManager` to prevent logic fragmentation.
- **Files**: `src/trading/order_manager.py`, `src/trading/portfolio_manager.py`, `src/trading/risk_manager.py`
