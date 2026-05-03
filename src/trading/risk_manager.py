"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_manager.py
Compatibility layer for RiskManager.
"""
from src.trading.risk_engine import RiskEngine as RiskManager, TradeSignal, DailyStats

__all__ = ["RiskManager", "TradeSignal", "DailyStats"]
