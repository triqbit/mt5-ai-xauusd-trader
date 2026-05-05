"""Trading modules: connectors and risk management."""

from __future__ import annotations

from src.trading.capital_allocator import (
    AllocationRequest,
    AllocationResult,
    CapitalAllocator,
    StrategyConfig,
)
from src.trading.mt5_connector import MT5Connector
from src.trading.risk_manager import DailyStats, RiskManager
from src.core.types import TradeSignalExecution as TradeSignal

__all__ = [
    "AllocationRequest",
    "AllocationResult",
    "CapitalAllocator",
    "DailyStats",
    "MT5Connector",
    "RiskManager",
    "StrategyConfig",
    "TradeSignal",
]
