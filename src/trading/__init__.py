"""Trading modules: connectors and risk management."""

from __future__ import annotations

from src.trading.backtester import Backtester, PerformanceReport
from src.trading.execution_filter import ExecutionFilter
from src.trading.mt5_connector import MT5Connector
from src.trading.risk_manager import DailyStats, RiskManager, TradeSignal

__all__ = [
    "Backtester",
    "DailyStats",
    "ExecutionFilter",
    "MT5Connector",
    "PerformanceReport",
    "RiskManager",
    "TradeSignal",
]
