"""Trading modules: connectors and risk management."""

from __future__ import annotations

from src.core.schemas import TradeSignal
from src.trading.capital_allocator import (
    AllocationRequest,
    AllocationResult,
    CapitalAllocator,
    RejectionCode,
    StrategyConfig,
)
from src.trading.mt5_connector import MT5Connector
from src.trading.risk_engine import RiskDecision, RiskEngine

__all__ = [
    "AllocationRequest",
    "AllocationResult",
    "CapitalAllocator",
    "MT5Connector",
    "RejectionCode",
    "RiskDecision",
    "RiskEngine",
    "StrategyConfig",
    "TradeSignal",
]
