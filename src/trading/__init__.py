"""Trading modules: connectors and risk management."""

from __future__ import annotations

from src.core.schemas import TradeSignal
from src.trading.capital_allocator import (
    AllocationRequest,
    AllocationResult,
    CapitalAllocator,
    StrategyConfig,
)
from src.trading.mt5_connector import MT5Connector
from src.trading.risk_engine import RiskDecision, RiskEngine
from src.trading.risk_manager import DailyStats, RiskManager

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
