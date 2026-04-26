# Architecture

This document describes the high-level architecture of the MT5 AI/ML Trading Bot.

## Overview

The system is composed of several modules:

- **Core**: Configuration, monitoring, and logging.
- **Trading**: MT5 connector, order management, and risk management.
- **Models**: AI/ML models (Ensemble, PPO, LSTM).
- **Environment**: Gymnasium environment for reinforcement learning.

## System Diagram

The following diagram illustrates the interaction between the core components during a live trading session.

```mermaid
sequenceDiagram
    participant M as Main Loop
    participant C as MT5 Connector
    participant E as Ensemble Model
    participant R as Risk Manager
    participant L as Trade Logger

    M->>C: Fetch OHLCV & Ticks
    C-->>M: Return Market Data
    M->>E: Predict Direction (Obs)
    E-->>M: Direction & Confidence
    M->>L: Log Signal
    M->>R: Size Position & Approve
    R->>R: 6-Layer Filter Cascade
    alt Approved
        R-->>M: Approved (Lot Size)
        M->>C: Place Market Order
        C-->>M: Order Ticket
        M->>L: Log Trade Execution
    else Rejected
        R-->>M: Rejected
        M->>L: Log Risk Event
    end
```

## Module Responsibilities

### 1. Core Module
- **Configuration**: Handles `.env` and environment variables.
- **Monitoring**: Equity tracking and Telegram alerts.
- **Logging**: SQLAlchemy-based trade and signal persistence.

### 2. Models Module
- **Ensemble**: Combines multiple RL and Deep Learning models.
- **Dynamic Weighting**: Adjusts model influence based on recent performance (Sharpe Ratio).

### 3. Trading Module
- **Connector**: Abstracts MT5 SDK and MetaAPI.
- **Risk Management**: Enforces strict drawdown and allocation rules.
- **Order Management**: Executes and tracks market orders.
