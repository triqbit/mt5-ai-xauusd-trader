# Trading Module

The `src/trading/` package handles market connectivity, order execution, and risk management.

## Components

- **mt5_connector.py**: Dual-path connector supporting native MetaTrader 5 SDK and MetaAPI cloud fallback.
- **risk_manager.py**: Multi-layer risk filter cascade and position sizing (Kelly Criterion).
- **order_manager.py**: High-level abstraction for placing and managing market orders.
- **portfolio_manager.py**: (In development) Multi-asset allocation and rebalancing.

## Usage

```python
from src.trading.mt5_connector import MT5Connector
from src.trading.risk_manager import RiskManager

connector = MT5Connector(config)
risk = RiskManager(config, balance=10000.0)

if connector.connect():
    # Trading logic
    pass
```
