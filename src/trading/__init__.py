"""Trading modules: connectors and risk management."""

from __future__ import annotations

from src.trading.capital_allocator import AllocationResult, CapitalAllocator, StrategyConfig
from src.trading.execution_filter import ExecutionDecision, ExecutionFilter
from src.trading.mt5_connector import MT5Connector
from src.trading.risk_manager import DailyStats, RiskManager, TradeSignal

__all__ = [
    "AllocationResult",
    "CapitalAllocator",
    "DailyStats",
    "ExecutionDecision",
    "ExecutionFilter",
    "MT5Connector",
    "RiskManager",
    "StrategyConfig",
    "TradeSignal",
]
