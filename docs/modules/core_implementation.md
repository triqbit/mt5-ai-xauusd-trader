# Core Implementation Details

This document outlines the implementation details of the core modules scaffolded in the enterprise structure.

## Configuration (src/core/config.py)
Uses Pydantic Settings V2 for robust environment variable management and validation.

## Connectivity (src/trading/mt5_connector.py)
Implements a dual-path strategy for MT5 connection:
1. Native SDK for Windows-based terminal.
2. MetaAPI cloud fallback for cross-platform support.

## Risk Engine (src/trading/risk_engine.py)
Enforces the 8-layer safety cascade and ATR-based position sizing as defined in RISK_LIMITS.md.

## Ensemble Model (src/models/ensemble.py)
Aggregates signals from PPO, Dreamer, and LSTM models using weighted consensus and dissent veto logic.
