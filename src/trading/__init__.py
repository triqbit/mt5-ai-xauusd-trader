"""Trading modules: connectors and risk management."""

from __future__ import annotations

from src.trading.capital_allocator import (
    AllocationRequest,
    AllocationResult,
    CapitalAllocator,
    StrategyConfig,
)
from src.trading.mt5_connector import MT5Connector
from src.trading.risk_engine import DailyStats, RiskDecision, RiskEngine
from src.trading.risk_manager import RiskManager, TradeSignal

__all__ = [
    "AllocationRequest",
    "AllocationResult",
    "CapitalAllocator",
    "DailyStats",
    "MT5Connector",
    "RiskDecision",
    "RiskEngine",
    "RiskManager",
    "StrategyConfig",
    "TradeSignal",
]
