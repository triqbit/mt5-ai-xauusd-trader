"""Trading modules: connectors and risk management."""

from __future__ import annotations

from src.core.schemas import TradeSignal
from src.trading.backtester import BacktestEngine, PerformanceReport
from src.trading.capital_allocator import (
    AllocationRequest,
    AllocationResult,
    CapitalAllocator,
    RejectionCode,
    StrategyConfig,
)
from src.trading.mt5_connector import MT5Connector
from src.trading.risk_manager import AuditedRiskManager, RiskManager

__all__ = [
    "AllocationRequest",
    "AllocationResult",
    "AuditedRiskManager",
    "BacktestEngine",
    "CapitalAllocator",
    "MT5Connector",
    "PerformanceReport",
    "RejectionCode",
    "RiskManager",
    "StrategyConfig",
    "TradeSignal",
]
