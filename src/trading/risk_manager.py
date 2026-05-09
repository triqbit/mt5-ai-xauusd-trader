"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_manager.py

Enterprise risk management engine implementing:
  - Kelly Criterion position sizing (fractional)
  - Ray Dalio All-Weather portfolio allocation
  - Dynamic drawdown protection & circuit breakers
  - 6-layer entry filter cascade

This module relies on the unified TradeSignal schema from src.core.schemas
to ensure all signals entering the risk engine are technically valid.

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
from src.core.schemas import TradeSignal
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


@dataclass
class RiskDecision:
    """Decision details from the RiskManager."""

    is_approved: bool
    reason: str = ""
    adjusted_lot_size: float = 0.0


class RiskManager:
    """
    Central risk authority.
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
        signal_id: Optional[int] = None,
        model_health: Optional[dict] = None,
        open_positions: Optional[List[Dict[str, Any]]] = None,
        market_data: Optional[pd.DataFrame] = None,
    ) -> bool:
        """
        Run the full 8-layer risk filter cascade.
        Returns True only if ALL layers pass.
        """
        decision = self.validate_signal(
            signal,
            market_data=market_data,
            open_positions=open_positions or [],
            model_health=model_health,
        )

        passed = decision.is_approved
        rejection_reason = decision.reason

        if not passed:
            logger.warning(
                "Signal REJECTED | %s %s | Reason: %s",
                signal.symbol,
                signal.direction,
                rejection_reason,
            )
            if self.trade_logger:
                self.trade_logger.log_risk_event(
                    event_type="SIGNAL_REJECTED",
                    description=rejection_reason,
                    symbol=signal.symbol,
                    signal_id=signal_id,
                )
        return passed

    def validate_signal(
        self,
        signal: TradeSignal,
        market_data: Optional[pd.DataFrame] = None,
        open_positions: Optional[List[Dict[str, Any]]] = None,
        model_health: Optional[dict] = None,
    ) -> RiskDecision:
        """
        Validate a trade signal against the 8-layer cascade.
        """
        # Layer 1: Circuit Breakers (Equity Drawdown)
        if not self._check_circuit_breaker():
            return RiskDecision(False, "Hard drawdown limit reached")

        # Layer 2: Daily Loss Limits (Institutional Cascading)
        if self.get_daily_loss_level() >= 4:
            return RiskDecision(False, "Daily loss limit reached (Level 4)")

        # Layer 3: Activity Limits
        active_positions = open_positions or []
        if not self._check_max_positions(len(active_positions)):
            return RiskDecision(False, "Max concurrent positions reached")
        if not self._check_consecutive_losses():
            return RiskDecision(False, "Max consecutive losses reached")

        # Layer 4: Exposure Limits
        if not self._check_directional_exposure(signal, active_positions):
            return RiskDecision(False, "Max directional exposure reached (30%)")
        if market_data is not None and not self._check_total_notional(
            signal, active_positions, market_data
        ):
            return RiskDecision(False, "Total notional exposure exceeds equity")

        # Layer 5: Symbol Allocation
        if not self._check_symbol_allocation(signal.symbol):
            return RiskDecision(False, f"Symbol {signal.symbol} not in approved list")

        # Layer 6: Prediction Limits
        if not self._check_minimum_confidence(signal.confidence):
            return RiskDecision(
                False, f"Confidence {signal.confidence:.2f} below {self.cfg.min_confidence}"
            )

        # Layer 7: Risk-Reward Validation (Min 1.5 R:R)
        if not self._check_risk_reward(signal):
            return RiskDecision(False, "Risk-Reward ratio below 1.5")

        # Layer 8: Model Health
        if not self._check_model_health(model_health):
            return RiskDecision(False, "Model health metrics below threshold")

        # Calculate lot size (Defaults to ATR-based if market_data present)
        if market_data is not None and not market_data.empty:
            adjusted_lots = self.calculate_position_size_atr(signal.symbol, market_data)
        else:
            # Fallback to config-based or Kelly if needed
            adjusted_lots = signal.lot_size

        if adjusted_lots < self.cfg.min_lot_size:
            return RiskDecision(False, f"Calculated lot size {adjusted_lots} below minimum")

        return RiskDecision(True, "Approved", adjusted_lots)

    def size_position(
        self,
        symbol: str,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        pip_value: float = 1.0,
    ) -> float:
        """
        Fractional Kelly Criterion position sizing.
        Returns lot size capped at max risk per trade.
        """
        if avg_loss == 0:
            return 0.01  # minimum lot
        kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        kelly_fraction = max(0.0, min(kelly_fraction, 0.25))  # cap at 25% Kelly
        risk_capital = self.balance * self.cfg.risk_per_trade
        lot_size = (risk_capital * kelly_fraction) / (avg_loss * pip_value)
        lot_size = max(0.01, round(lot_size, 2))
        logger.debug(
            "Kelly sizing | kelly=%.3f risk_cap=%.2f lots=%.2f",
            kelly_fraction,
            risk_capital,
            lot_size,
        )
        return lot_size

    def calculate_position_size_atr(self, symbol: str, market_data: pd.DataFrame) -> float:
        """
        ATR-based position sizing according to RISK_LIMITS.md.
        """
        if market_data.empty or "atr" not in market_data.columns:
            return self.cfg.min_lot_size

        current_atr = market_data["atr"].iloc[-1]
        avg_atr = market_data["atr"].tail(8640).mean()  # Approx 30 days of M5

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

    # -- Private filter layers ----------------------------------------------
    def _check_consecutive_losses(self) -> bool:
        if self.daily.consecutive_losses >= self.cfg.max_losing_streak:
            logger.warning(
                "Losing streak limit hit: %d (Limit: %d)",
                self.daily.consecutive_losses,
                self.cfg.max_losing_streak,
            )
            return False
        return True

    def _check_model_health(self, health: Optional[dict]) -> bool:
        if health is None:
            return True

        drift = float(health.get("drift", 0.0))
        accuracy = float(health.get("accuracy", 1.0))
        calibration = float(health.get("calibration", 0.0))

        if drift > self.cfg.model_drift_threshold:
            logger.warning(
                "Model drift too high: %.2f > %.2f", drift, self.cfg.model_drift_threshold
            )
            return False
        if accuracy < self.cfg.model_accuracy_floor:
            logger.warning(
                "Model accuracy too low: %.2f < %.2f", accuracy, self.cfg.model_accuracy_floor
            )
            return False
        if calibration > self.cfg.model_calibration_threshold:
            logger.warning(
                "Model calibration error too high: %.2f > %.2f",
                calibration,
                self.cfg.model_calibration_threshold,
            )
            return False

        return True

    def _check_circuit_breaker(self) -> bool:
        drawdown = (self.peak_equity - self.balance) / self.peak_equity
        if drawdown >= 0.15:  # 15% peak-to-valley kills all trading
            logger.critical(
                "CIRCUIT BREAKER: drawdown=%.1f%% - trading halted",
                drawdown * 100,
            )
            if self.trade_logger:
                self.trade_logger.log_risk_event(
                    event_type="CIRCUIT_BREAKER",
                    description=f"Drawdown {drawdown * 100:.1f}% hit 15% limit",
                )
            if self.monitor:
                self.monitor.alert_circuit_breaker(drawdown)
            return False
        return True

    def _check_daily_loss(self) -> bool:
        """Legacy check maintained for compatibility."""
        return self.get_daily_loss_level() < 4

    def get_daily_loss_level(self) -> int:
        """
        Institutional Daily Loss Level (0-4).
        """
        if self.daily.peak_equity <= 0 or self.daily.realised_pnl >= 0:
            return 0

        loss_pct = abs(self.daily.realised_pnl) / self.daily.peak_equity

        if loss_pct >= self.cfg.max_daily_loss:
            return 4
        if loss_pct >= (getattr(self.cfg, "daily_loss_lvl3", self.cfg.max_daily_loss * 0.75)):
            return 3
        if loss_pct >= (getattr(self.cfg, "daily_loss_lvl2", self.cfg.max_daily_loss * 0.5)):
            return 2
        if loss_pct >= (getattr(self.cfg, "daily_loss_lvl1", self.cfg.max_daily_loss * 0.25)):
            return 1
        return 0

    def get_size_multiplier_from_loss(self) -> float:
        """Multiplier based on daily loss level."""
        level = self.get_daily_loss_level()
        mapping = {0: 1.0, 1: 1.0, 2: 0.5, 3: 0.25, 4: 0.0}
        return mapping.get(level, 0.0)

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
        """Layer 4: Total notional < 100% equity (configured)."""
        total_lots = sum(pos.get("volume", 0.0) for pos in open_positions) + self.cfg.min_lot_size
        price = market_data["close"].iloc[-1] if not market_data.empty else 2300.0
        total_notional = total_lots * price * 100
        limit_pct = getattr(self.cfg, "max_total_notional_pct", 1.0)
        return total_notional < (self.balance * limit_pct)

    def _check_max_positions(self, open_positions_count: Optional[int] = None) -> bool:
        count = (
            open_positions_count
            if open_positions_count is not None
            else len(self.open_positions)
        )
        if count >= self.cfg.max_positions:
            logger.debug("Max positions reached (%d)", self.cfg.max_positions)
            return False
        return True

    def _check_symbol_allocation(self, symbol: str) -> bool:
        """Block trading on symbols not in the All-Weather portfolio."""
        if symbol not in ALLOCATION_WEIGHTS:
            logger.warning("Symbol %s not in approved portfolio", symbol)
            return False
        return True

    def _check_minimum_confidence(self, confidence: float, threshold: float = 0.55) -> bool:
        if confidence < threshold:
            logger.debug("Confidence %.2f below threshold %.2f", confidence, threshold)
            return False
        return True

    def _check_risk_reward(self, signal: TradeSignal, min_rr: float = 1.5) -> bool:
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.entry_price)
        if risk == 0:
            return False
        rr = reward / risk
        if rr < min_rr:
            logger.debug("R:R %.2f below minimum %.2f", rr, min_rr)
            return False
        return True


__all__ = ["ALLOCATION_WEIGHTS", "DailyStats", "RiskDecision", "RiskManager"]
