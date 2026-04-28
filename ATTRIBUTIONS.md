# Project Attributions

This project integrates several open-source modules and libraries. We are grateful to the following authors and projects for their contributions to the trading community.

---

## Integrated Trading Modules

### [zero-was-here/tradingbot](https://github.com/zero-was-here/tradingbot)
- **License:** MIT
- **Copyright:** zero-was-here (2024)
- **Components:** PPO algorithm, Dreamer V3 algorithm, 140+ feature engineering, Multi-timeframe analysis.
- **Location:** `src/core/rl_algorithms/ppo/`

### [ilahuerta-IA/mt5_live_trading_bot](https://github.com/ilahuerta-IA/mt5_live_trading_bot)
- **License:** MIT
- **Copyright:** ilahuerta-IA (2024)
- **Components:** Ray Dalio portfolio allocation, 6-layer entry filter system, State machine architecture, Real-time trading monitor.
- **Location:** `src/core/risk_management/` and `src/core/features/`

### [CodeDestroyer19/Neural-Network-MT5-Trading-Bot](https://github.com/CodeDestroyer19/Neural-Network-MT5-Trading-Bot)
- **License:** MIT
- **Copyright:** CodeDestroyer19 (2023)
- **Components:** Neural network architecture, Technical indicator calculations, Trade execution system.
- **Location:** `src/core/rl_algorithms/neural_networks/`

### [AminHP/gym-mtsim](https://github.com/AminHP/gym-mtsim)
- **License:** MIT
- **Copyright:** AminHP (2022)
- **Components:** OpenAI Gym environment wrapper, MetaTrader 5 simulator, Backtesting engine.
- **Location:** `src/core/environments/gym_mt5/`

### [Stefodan21/Forex-trading-bot](https://github.com/Stefodan21/Forex-trading-bot)
- **License:** MIT
- **Copyright:** Stefodan21 (2023)
- **Components:** PPO algorithm variant, GPU acceleration (DirectML/OpenCL), Dynamic position sizing.
- **Location:** `src/core/rl_algorithms/ppo_gpu/`

### [geraked/metatrader5](https://github.com/geraked/metatrader5)
- **License:** MIT
- **Copyright:** geraked (2023)
- **Components:** MQL5 trading strategies, Expert Advisor templates.
- **Location:** `strategies/templates/`

### [nguyenviettuan96/mt5_AI_trading_bot](https://github.com/nguyenviettuan96/mt5_AI_trading_bot)
- **License:** Apache 2.0
- **Copyright:** nguyenviettuan96 (2023)
- **Components:** LSTM neural network, Reinforcement learning integration, Feature extraction pipeline.
- **Location:** `src/core/rl_algorithms/lstm/`

---

## Core Libraries

The system relies on several enterprise-grade libraries:
- **PyTorch**: Deep learning and neural network execution.
- **Stable-Baselines3**: Reinforcement learning framework.
- **Gymnasium**: Standard API for reinforcement learning environments.
- **SQLAlchemy & Alembic**: Database ORM and migration management.
- **FastAPI**: High-performance API framework for the dashboard.
- **MetaTrader5**: Official Python integration for MetaTrader 5.

For a full list of third-party dependencies and their licenses, see [docs/DEPENDENCY_LICENSES.md](docs/DEPENDENCY_LICENSES.md).
