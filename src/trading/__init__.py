"""Trading modules: connectors and risk management."""

from __future__ import annotations

from src.trading.mt5_connector import MT5Connector
from src.trading.risk_manager import DailyStats, RiskManager, TradeSignal

# Alias for architectural consistency
RiskEngine = RiskManager

__all__ = ["DailyStats", "MT5Connector", "RiskEngine", "RiskManager", "TradeSignal"]
