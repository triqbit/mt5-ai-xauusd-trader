"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_manager.py

Enterprise risk management engine implementing:
  - ATR-based position sizing (14-period vs 30-day average)
  - Cascading daily loss circuit breakers (Level 1-4)
  - Drawdown safeguards and exposure limits
  - 8-layer safety cascade signal validation

This module relies on the unified TradeSignal and RiskDecision schemas from src.core.schemas.

Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

import pandas as pd

from src.core.config import TradingConfig
from src.core.monitor import Monitor
from src.core.schemas import RiskDecision, TradeSignal
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


@dataclass
class DailyStats:
    """Intraday PnL tracker reset each trading day."""

    date: date = field(default_factory=date.today)
    realised_pnl: float = 0.0
    trade_count: int = 0
    peak_equity: float = 0.0
    consecutive_losses: int = 0


class RiskManager:
    """
    Central risk authority.
    Enforces institutional safeguards via an 8-layer cascade.
    Every signal must be approved here before reaching the order router.
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
        self.open_positions: Dict[str, int] = {}  # symbol -> ticket
        self.trade_logger = logger_db
        self.monitor = monitor
        logger.info("RiskManager initialised | balance=%.2f", account_balance)

    # -- Public API ---------------------------------------------------------
    def approve(
        self,
        signal: TradeSignal,
        market_data: pd.DataFrame,
        open_positions: List[Dict[str, Any]],
        signal_id: Optional[int] = None,
        model_health: Optional[dict] = None,
    ) -> RiskDecision:
        """
        Run the full 8-layer risk filter cascade.
        Returns a RiskDecision object.
        """
        trace = {}

        # Layer 1: Circuit Breakers (Equity Drawdown)
        trace["circuit_breaker"] = self._check_drawdown_breaker()
        if not trace["circuit_breaker"]:
            return self._create_rejection("Hard drawdown limit reached", trace)

        # Layer 2: Daily Loss Limits (Level 4)
        trace["daily_loss"] = self.get_daily_loss_level() < 4
        if not trace["daily_loss"]:
            return self._create_rejection("Daily loss limit reached (Level 4)", trace)

        # Layer 3: Activity Limits
        trace["max_daily_trades"] = self.daily.trade_count < self.cfg.max_trades_per_day
        if not trace["max_daily_trades"]:
            return self._create_rejection("Max daily trades reached", trace)

        trace["consecutive_losses"] = self.daily.consecutive_losses < self.cfg.max_losing_streak
        if not trace["consecutive_losses"]:
            return self._create_rejection("Max consecutive losses reached", trace)

        # Layer 4: Exposure Limits
        trace["max_concurrent_positions"] = len(open_positions) < self.cfg.max_positions
        if not trace["max_concurrent_positions"]:
            return self._create_rejection("Max concurrent positions reached", trace)

        trace["directional_exposure"] = self._check_directional_exposure(signal, open_positions)
        if not trace["directional_exposure"]:
            return self._create_rejection("Max directional exposure reached (30%)", trace)

        trace["total_notional"] = self._check_total_notional(signal, open_positions, market_data)
        if not trace["total_notional"]:
            return self._create_rejection("Total notional exposure exceeds equity", trace)

        # Layer 5: Symbol Allocation
        trace["symbol_allocation"] = self._check_symbol_allocation(signal.symbol)
        if not trace["symbol_allocation"]:
            return self._create_rejection(f"Symbol {signal.symbol} not in approved list", trace)

        # Layer 6: Prediction Limits
        trace["min_confidence"] = signal.confidence >= self.cfg.min_confidence
        if not trace["min_confidence"]:
            return self._create_rejection(
                f"Confidence {signal.confidence:.2f} below {self.cfg.min_confidence}", trace
            )

        # Layer 7: Risk-Reward Validation (Min 1.5 R:R)
        trace["risk_reward"] = self._check_risk_reward(signal)
        if not trace["risk_reward"]:
            return self._create_rejection("Risk-Reward ratio below 1.5", trace)

        # Layer 8: Model Health
        trace["model_health"] = self._check_model_health(model_health)
        if not trace["model_health"]:
            return self._create_rejection("Model health metrics below threshold", trace)

        # Calculate final lot size using ATR-based sizing
        adjusted_lots = self.calculate_position_size(signal.symbol, market_data)

        if adjusted_lots < self.cfg.min_lot_size:
            return self._create_rejection(
                f"Calculated lot size {adjusted_lots} below minimum", trace
            )

        decision = RiskDecision(
            is_approved=True,
            reason="Approved",
            adjusted_lot_size=adjusted_lots,
            trace=trace,
        )

        logger.info(
            "Signal APPROVED | %s %s | Lots: %.2f",
            signal.symbol,
            signal.direction,
            adjusted_lots,
        )
        return decision

    def _create_rejection(self, reason: str, trace: dict) -> RiskDecision:
        """Helper to create and log a rejected RiskDecision."""
        decision = RiskDecision(
            is_approved=False,
            reason=reason,
            adjusted_lot_size=0.0,
            trace=trace,
        )
        logger.warning("Signal REJECTED | Reason: %s", reason)
        if self.trade_logger:
            self.trade_logger.log_risk_event(
                event_type="SIGNAL_REJECTED",
                description=reason,
            )
        return decision

    def calculate_position_size(self, symbol: str, market_data: pd.DataFrame) -> float:
        """
        ATR-based position sizing according to RISK_LIMITS.md.

        Logic:
          - Compare 14-period ATR to 30-day average.
          - Normal Volatility: 100% position size.
          - High Volatility (>1.5x): Reduce to 75% position size.
          - Very High Volatility (>2x): Reduce to 50% position size.
          - Extreme Volatility (>3x): HALT (0.0 lots).

        Additional Constraints:
          - Daily loss level multiplier (100%, 50%, 25%, 0%).
          - Max Position Size (10% of account equity per trade).

        Args:
            symbol: Trading symbol.
            market_data: DataFrame with 'atr' and 'close'.

        Returns:
            float: Calculated lot size.
        """
        if market_data.empty or "atr" not in market_data.columns:
            return self.cfg.min_lot_size

        current_atr = market_data["atr"].iloc[-1]
        # Approx 30 days of M5 (8640 bars)
        avg_atr = market_data["atr"].tail(8640).mean()

        vol_multiplier = 1.0
        ratio = current_atr / avg_atr if avg_atr > 0 else 1.0

        if ratio > self.cfg.volatility_extreme_threshold:
            return 0.0
        elif ratio > self.cfg.volatility_very_high_threshold:
            vol_multiplier = 0.5
        elif ratio > self.cfg.volatility_high_threshold:
            vol_multiplier = 0.75

        loss_multiplier = self.get_size_multiplier_from_loss()
        total_multiplier = vol_multiplier * loss_multiplier

        if total_multiplier <= 0:
            return 0.0

        # Sizing: risk 1% (cfg.risk_per_trade) of balance
        risk_amount = self.balance * self.cfg.risk_per_trade
        # ATR * 100 converts gold ATR to $ per lot
        lot_size = (risk_amount / (current_atr * 100)) * total_multiplier

        # Cap at Max Position Size (10% of equity)
        max_notional = self.balance * self.cfg.max_position_size_pct
        price = market_data["close"].iloc[-1]
        max_lots = max_notional / (price * 100)

        final_lots = min(lot_size, max_lots)
        final_lots = max(self.cfg.min_lot_size, round(final_lots, 2))

        return final_lots

    def update_equity(self, current_equity: float) -> None:
        """Call after every closed trade or on heartbeat."""
        self.balance = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        if current_equity > self.daily.peak_equity:
            self.daily.peak_equity = current_equity

    def record_pnl(self, pnl: float) -> None:
        """Accumulate intraday realised PnL."""
        self.daily.realised_pnl += pnl
        self.daily.trade_count += 1
        if pnl < 0:
            self.daily.consecutive_losses += 1
        else:
            self.daily.consecutive_losses = 0

    def reset_daily(self) -> None:
        """Must be called at the start of each trading day."""
        if self.monitor:
            self.monitor.send_daily_summary(self.daily.realised_pnl, self.daily.trade_count)
        self.daily = DailyStats(peak_equity=self.balance)
        logger.info("Daily stats reset")

    # -- Internal cascade layers -------------------------------------------

    def _check_drawdown_breaker(self) -> bool:
        """Layer 1: Equity Drawdown."""
        if self.peak_equity <= 0:
            return True
        drawdown = (self.peak_equity - self.balance) / self.peak_equity
        if drawdown >= self.cfg.max_drawdown:
            logger.critical("CIRCUIT BREAKER: Drawdown %.2f%% hit limit", drawdown * 100)
            if self.monitor:
                self.monitor.alert_circuit_breaker(drawdown)
            return False
        return True

    def get_daily_loss_level(self) -> int:
        """Layer 2: Daily Loss Level (0-4)."""
        if self.daily.peak_equity <= 0 or self.daily.realised_pnl >= 0:
            return 0

        loss_pct = abs(self.daily.realised_pnl) / self.daily.peak_equity

        if loss_pct >= self.cfg.max_daily_loss:
            return 4
        if loss_pct >= self.cfg.daily_loss_lvl3:
            return 3
        if loss_pct >= self.cfg.daily_loss_lvl2:
            return 2
        if loss_pct >= self.cfg.daily_loss_lvl1:
            return 1
        return 0

    def _check_directional_exposure(
        self, signal: TradeSignal, open_positions: List[Dict[str, Any]]
    ) -> bool:
        """Layer 4: 30% net directional exposure."""
        net_lots = 0.0
        for pos in open_positions:
            vol = pos.get("volume", 0.0)
            if pos.get("type") == 0:  # BUY
                net_lots += vol
            else:  # SELL
                net_lots -= vol

        net_lots += self.cfg.min_lot_size if signal.direction > 0 else -self.cfg.min_lot_size
        price_estimate = 2300.0  # Gold estimate
        notional = abs(net_lots) * price_estimate * 100
        exposure_pct = notional / self.balance if self.balance > 0 else 1.0

        return exposure_pct <= self.cfg.max_single_direction_pct

    def _check_total_notional(
        self, signal: TradeSignal, open_positions: List[Dict[str, Any]], market_data: pd.DataFrame
    ) -> bool:
        """Layer 4: Total notional < 100% equity."""
        total_lots = sum(pos.get("volume", 0.0) for pos in open_positions) + self.cfg.min_lot_size
        price = market_data["close"].iloc[-1] if not market_data.empty else 2300.0
        total_notional = total_lots * price * 100
        return total_notional < (self.balance * self.cfg.max_total_notional_pct)

    def _check_symbol_allocation(self, symbol: str) -> bool:
        """Layer 5: Approved Portfolio."""
        return symbol in ALLOCATION_WEIGHTS

    def _check_risk_reward(self, signal: TradeSignal, min_rr: float = 1.5) -> bool:
        """Layer 7: Minimum 1.5 Risk-Reward."""
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.entry_price)
        return reward >= (risk * min_rr) if risk > 0 else False

    def _check_model_health(self, health: Optional[Dict[str, float]]) -> bool:
        """Layer 8: Model Health Metrics."""
        if health is None:
            return True

        if health.get("drift", 0.0) > self.cfg.model_drift_threshold:
            return False
        if health.get("accuracy", 1.0) < self.cfg.model_accuracy_floor:
            return False
        return health.get("calibration", 0.0) <= self.cfg.model_calibration_threshold

    def get_size_multiplier_from_loss(self) -> float:
        """Multiplier based on daily loss level."""
        level = self.get_daily_loss_level()
        mapping = {0: 1.0, 1: 1.0, 2: 0.5, 3: 0.25, 4: 0.0}
        return mapping.get(level, 0.0)


__all__ = ["ALLOCATION_WEIGHTS", "DailyStats", "RiskManager"]
