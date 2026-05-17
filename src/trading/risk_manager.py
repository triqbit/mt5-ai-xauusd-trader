"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_manager.py

Institutional risk engine implementing the 8-layer safety cascade.
Standardized for system-wide harmonization.

Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from src.core.config import TradingConfig
from src.core.monitor import Monitor
from src.core.schemas import DailyStats, RiskDecision, TradeSignal
from src.core.trade_logger import TradeLogger

logger = logging.getLogger(__name__)

# Ray Dalio All-Weather allocation weights
ALLOCATION_WEIGHTS: Dict[str, float] = {
    "XAUUSD": 0.18,  # Gold - inflation hedge
    "USDCHF": 0.15,  # CHF - deflation hedge
    "GBPUSD": 0.13,  # GBP - growth / balanced
    "EURUSD": 0.12,  # EUR - growth / balanced
    "XAGUSD": 0.12,  # Silver - commodity
    "AUDUSD": 0.15,  # AUD - commodity currency
    "USDJPY": 0.08,  # JPY - carry trade
    "EURJPY": 0.07,  # EUR/JPY cross
}


class RiskManager:
    """
    Institutional risk engine.
    Enforces RISK_LIMITS.md safeguards via an 8-layer cascade.
    """

    def __init__(
        self,
        config: TradingConfig,
        account_balance: float,
        logger_db: Optional[TradeLogger] = None,
        monitor: Optional[Monitor] = None,
    ) -> None:
        self.cfg = config
        self.balance = account_balance
        self.peak_equity = account_balance
        self.daily = DailyStats(peak_equity=account_balance)
        self.trade_logger = logger_db
        self.monitor = monitor
        self.open_positions: Dict[str, int] = {}  # symbol -> ticket
        logger.info("RiskManager initialised | balance=%.2f", account_balance)

    def validate_signal(
        self,
        signal: TradeSignal,
        market_data: pd.DataFrame,
        open_positions: List[Dict[str, Any]],
        model_health: Optional[Dict[str, float]] = None,
    ) -> RiskDecision:
        """
        Validate a trade signal against the 8-layer cascade.
        """
        if not self._check_circuit_breaker():
            return RiskDecision(is_approved=False, reason="Circuit breaker: hard drawdown limit reached")

        if self._get_daily_loss_level() >= 4:
            return RiskDecision(is_approved=False, reason="Daily loss limit reached")

        if self.daily.trade_count >= self.cfg.max_trades_per_day:
            return RiskDecision(is_approved=False, reason="Max daily trades reached")
        if self.daily.consecutive_losses >= self.cfg.max_losing_streak:
            return RiskDecision(is_approved=False, reason="Max consecutive losses reached")

        if len(open_positions) >= self.cfg.max_positions:
            return RiskDecision(is_approved=False, reason="Max concurrent positions reached")
        if not self._check_directional_exposure(signal, open_positions):
            return RiskDecision(is_approved=False, reason="Max directional exposure reached (30%)")
        if not self._check_total_notional(signal, open_positions, market_data):
            return RiskDecision(is_approved=False, reason="Total notional exposure exceeds equity")

        if signal.symbol not in ALLOCATION_WEIGHTS:
            return RiskDecision(is_approved=False, reason=f"Symbol {signal.symbol} not in approved list")

        if signal.confidence < self.cfg.min_confidence:
            return RiskDecision(
                is_approved=False, reason=f"Confidence {signal.confidence:.2f} below {self.cfg.min_confidence}"
            )

        if not self._check_risk_reward(signal):
            return RiskDecision(is_approved=False, reason="Risk-Reward ratio below 1.5")

        if not self._check_model_health(model_health):
            return RiskDecision(is_approved=False, reason="Model health metrics below threshold")

        adjusted_lots = self.calculate_position_size(signal.symbol, market_data)

        if adjusted_lots < self.cfg.min_lot_size:
            return RiskDecision(is_approved=False, reason=f"Calculated lot size {adjusted_lots} below minimum")

        return RiskDecision(is_approved=True, reason="Approved", adjusted_lot_size=adjusted_lots)

    def calculate_position_size(self, symbol: str, market_data: pd.DataFrame) -> float:
        atr_col = "atr"
        if "atr" not in market_data.columns:
            for col in market_data.columns:
                if "atr" in col.lower():
                    atr_col = col
                    break

        if market_data.empty or atr_col not in market_data.columns:
            return self.cfg.min_lot_size

        current_atr = market_data[atr_col].iloc[-1]
        avg_atr = market_data[atr_col].tail(8640).mean()

        vol_multiplier = 1.0
        ratio = current_atr / avg_atr if avg_atr > 0 else 1.0

        if ratio > self.cfg.volatility_extreme_threshold:
            return 0.0
        elif ratio > self.cfg.volatility_very_high_threshold:
            vol_multiplier = 0.5
        elif ratio > self.cfg.volatility_high_threshold:
            vol_multiplier = 0.75

        loss_multiplier = self._get_size_multiplier_from_loss()
        total_multiplier = vol_multiplier * loss_multiplier

        if total_multiplier <= 0:
            return 0.0

        risk_amount = self.balance * self.cfg.risk_per_trade
        lot_size = (risk_amount / (current_atr * 100)) * total_multiplier

        max_notional = self.balance * self.cfg.max_position_size_pct
        price = market_data["close"].iloc[-1]
        max_lots = max_notional / (price * 100)

        final_lots = min(lot_size, max_lots)
        if final_lots <= 0:
            return 0.0
        final_lots = max(self.cfg.min_lot_size, round(final_lots, 2))

        return final_lots

    def size_position(self, symbol: str, market_data: Optional[pd.DataFrame] = None, *args, **kwargs) -> float:
        """Legacy support for main.py."""
        if market_data is not None:
            return self.calculate_position_size(symbol, market_data)
        return self.cfg.min_lot_size

    def update_equity(self, current_equity: float) -> None:
        self.balance = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        if current_equity > self.daily.peak_equity:
            self.daily.peak_equity = current_equity

    def record_pnl(self, pnl: float) -> None:
        self.daily.realised_pnl += pnl
        self.daily.trade_count += 1
        if pnl < 0:
            self.daily.consecutive_losses += 1
        else:
            self.daily.consecutive_losses = 0

    def reset_daily(self) -> None:
        self.daily = DailyStats(peak_equity=self.balance)
        logger.info("Daily stats reset")

    def approve(self, signal: TradeSignal, *args, **kwargs) -> bool:
        """Legacy approve method."""
        return signal.confidence >= self.cfg.min_confidence

    # -- Internal cascade layers -------------------------------------------

    def _check_circuit_breaker(self) -> bool:
        if self.peak_equity <= 0:
            return True
        drawdown = (self.peak_equity - self.balance) / self.peak_equity
        return drawdown < self.cfg.max_drawdown

    def _get_daily_loss_level(self) -> int:
        if self.daily.peak_equity <= 0 or self.daily.realised_pnl >= 0:
            return 0
        loss_pct = abs(self.daily.realised_pnl) / self.daily.peak_equity
        return 4 if loss_pct >= self.cfg.max_daily_loss else 0

    def _check_daily_loss(self) -> bool:
        return self._get_daily_loss_level() < 4

    def _check_max_positions(self) -> bool:
        return True # Handled in validate_signal

    def _check_symbol_allocation(self, symbol: str) -> bool:
        return symbol in ALLOCATION_WEIGHTS

    def _check_minimum_confidence(self, confidence: float) -> bool:
        return confidence >= self.cfg.min_confidence

    def _check_risk_reward(self, signal: TradeSignal) -> bool:
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.entry_price)
        return reward >= (risk * 1.5) if risk > 0 else False

    def _check_consecutive_losses(self) -> bool:
        return self.daily.consecutive_losses < self.cfg.max_losing_streak

    def _check_model_health(self, health: Optional[Dict[str, float]]) -> bool:
        if health is None: return True
        return (health.get("drift", 0.0) <= self.cfg.model_drift_threshold and
                health.get("accuracy", 1.0) >= self.cfg.model_accuracy_floor)

    def _check_directional_exposure(self, signal: TradeSignal, open_positions: List[Dict[str, Any]]) -> bool:
        net_lots = sum(p.get("volume", 0.0) * (1 if p.get("type") == 0 else -1) for p in open_positions)
        net_lots += self.cfg.min_lot_size * (1 if signal.direction > 0 else -1)
        exposure = abs(net_lots) * 2300 * 100 / self.balance if self.balance > 0 else 1.0
        return exposure <= self.cfg.max_single_direction_pct

    def _check_total_notional(self, signal: TradeSignal, open_positions: List[Dict[str, Any]], market_data: pd.DataFrame) -> bool:
        total_lots = sum(p.get("volume", 0.0) for p in open_positions) + self.cfg.min_lot_size
        price = market_data["close"].iloc[-1] if not market_data.empty else 2300.0
        return (total_lots * price * 100) < (self.balance * self.cfg.max_total_notional_pct)

    def _get_size_multiplier_from_loss(self) -> float:
        return 0.0 if self._get_daily_loss_level() >= 4 else 1.0

__all__ = ["RiskManager"]
