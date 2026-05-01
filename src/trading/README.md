# Trading Module

The `src/trading` module contains the core trading logic, including connectivity to MetaTrader 5, risk management, and order execution.

## Modules

- **`mt5_connector.py`**: Manages the connection to the MT5 terminal. It provides a unified interface for fetching market data, checking account info, and placing orders. It also supports MetaAPI as a cloud fallback.
- **`risk_manager.py`**: The "Central Risk Authority." It implements a 6-layer filter cascade to validate signals before execution.
- **`portfolio_manager.py`**: (If implemented) Manages multi-symbol exposure and global risk parity.
- **`order_manager.py`**: Handles low-level order routing and tracking.

## Risk Management Layers

Every trade must pass through these filters:
1. **Circuit Breaker**: Total drawdown limit.
2. **Daily Loss**: Max allowed loss per day.
3. **Max Positions**: Limit on concurrent open trades.
4. **Symbol Allocation**: Portfolio weight checks.
5. **Minimum Confidence**: AI model confidence threshold.
6. **Risk-Reward**: Minimum R:R ratio (default 1.5).

## Usage Example

```python
from src.trading.mt5_connector import MT5Connector
from src.trading.risk_manager import RiskManager

connector = MT5Connector()
risk = RiskManager(cfg, account_balance=10000)

if risk.approve(signal):
    connector.place_order(signal)
```
