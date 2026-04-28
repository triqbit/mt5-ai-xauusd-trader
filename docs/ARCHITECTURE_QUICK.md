# 🏛️ Architecture Quick Overview

This document provides a high-level technical map of the MT5 AI/ML Trading Bot for engineers and contributors.

## 🧩 System Components

The system is organized into four core functional domains within the `src/` directory:

### 1. `src/core/` (The Backbone)
- **`config.py`**: Centralized, type-safe configuration using Pydantic V2. Manages environment variables and secrets.
- **`trade_logger.py`**: Structured logging of all signals and executed trades to a database (PostgreSQL/SQLite).
- **`monitor.py`**: Real-time metric tracking (equity, performance) for observability.

### 2. `src/models/` (The Brain)
- **`ppo_agent.py`**: Implementation of Proximal Policy Optimization for reinforcement learning.
- **`ensemble.py`**: Consensus logic that aggregates predictions from multiple models (PPO, LSTM, etc.) to reduce variance.
- **`transformer_model.py`**: Advanced time-series processing using attention mechanisms.

### 3. `src/trading/` (The Hands)
- **`mt5_connector.py`**: Low-level wrapper for the MetaTrader 5 Python SDK. Handles connection, data fetching, and order submission.
- **`risk_manager.py`**: The critical safety gate. Implements position sizing (Kelly Criterion), daily loss limits, and signal validation.
- **`order_manager.py`**: Higher-level logic for managing trade lifecycles, stops, and targets.

### 4. `src/environment/` (The Training Ground)
- **`gym_env.py`**: A specialized Gymnasium environment that simulates market dynamics for training Reinforcement Learning agents.

## 🔄 Core Data Flow

1. **Ingestion**: `MT5Connector` polls real-time OHLCV and tick data from MetaTrader 5.
2. **Observation**: Data is processed into feature vectors (via `gym_env.py` or feature engineering modules).
3. **Inference**: `EnsembleModel` generates a trading signal (Buy/Sell/Hold) based on the combined intelligence of underlying agents.
4. **Validation**: `RiskManager` evaluates the signal against account equity, current exposure, and volatility (ATR).
5. **Execution**: If approved, `OrderManager` submits the trade via `MT5Connector`.
6. **Persistence**: `TradeLogger` records the signal and trade details for future audit and performance analysis.

## 🛠️ Tech Stack Highlights
- **Framework**: PyTorch & Stable-Baselines3
- **Platform**: MetaTrader 5 (MT5)
- **Validation**: Pydantic V2 & MyPy
- **Observability**: Prometheus & Structlog

---
*For detailed implementation standards, see [ENTERPRISE_STANDARDS.md](../ENTERPRISE_STANDARDS.md).*
