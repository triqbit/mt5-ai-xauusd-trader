# System Architecture

The MT5 AI/ML Trading Bot is designed with a modular, decoupled architecture to ensure reliability, testability, and cross-platform support.

## High-Level Overview

```mermaid
graph TD
    subgraph "AI/ML Brain"
        Ensemble[Ensemble Model]
        PPO[PPO Agent]
        Dreamer[Dreamer V3]
        LSTM[LSTM + Attention]
        Ensemble --> PPO
        Ensemble --> Dreamer
        Ensemble --> LSTM
    end

    subgraph "Trading Engine"
        RM[Risk Manager]
        MC[MT5 Connector]
        TL[Trade Logger]
    end

    MarketData[(Market Data)] --> MC
    MC --> Observation[Market Observation]
    Observation --> Ensemble
    Ensemble --> Signal[Raw Signal]
    Signal --> RM
    RM -- "Approve" --> MC
    MC -- "Execute" --> Broker[MT5 Terminal / MetaAPI]

    RM -- "Log" --> TL
    MC -- "Log" --> TL
    Broker -- "Update" --> TL
```

## Signal Flow

1.  **Ingestion**: `MT5Connector` fetches the latest OHLCV data from MetaTrader 5.
2.  **Observation**: Data is processed into features (140+ indicators).
3.  **Inference**: `EnsembleModel` aggregates predictions from RL and Neural Network agents.
4.  **Validation**: `RiskManager` runs a 6-layer filter cascade (Circuit Breakers, Daily Loss, etc.).
5.  **Execution**: Validated signals are converted into orders via `MT5Connector`.
6.  **Persistence**: All events (Signals, Trades, Rejections) are recorded in the `TradeLogger`.

## Component Responsibilities

- **Core**: Configuration management and system-wide monitoring.
- **Models**: Architecture definition, training, and inference.
- **Environment**: Gymnasium-compatible wrappers for RL training.
- **Trading**: Platform connectivity and risk authority.
