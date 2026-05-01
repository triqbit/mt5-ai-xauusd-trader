"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_engine.py
Enterprise risk management engine implementing:
  - ATR-based position sizing
  - Cascading daily loss limits
  - Equity drawdown protection circuit breakers
  - Institutional risk constraints (max leverage, positions)
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Dict, Optional

from src.core.config import TradingConfig
from src.core.monitor import Monitor
from src.core.trade_logger import TradeLogger

logger = logging.getLogger(__name__)


@dataclass
class TradeSignal:
    """Validated trading signal passed to order execution."""

    symbol: str
    direction: int  # +1 buy / -1 sell
    entry_price: float
    stop_loss: float
    take_profit: float
    lot_size: float
    algorithm: str
    confidence: float  # 0.0 - 1.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DailyRiskStats:
    """Intraday PnL tracker reset each trading day."""

    date: date = field(default_factory=lambda: datetime.now(timezone.utc).date())
    realised_pnl: float = 0.0
    trade_count: int = 0
    peak_equity: float = 0.0
    consecutive_losses: int = 0


class RiskEngine:
    """
    Central risk authority implementing RISK_LIMITS.md.
    Enforces cascading limits and ATR-based position sizing.
    """

    def __init__(
        self,
        config: TradingConfig,
        account_balance: float,
        logger_db: Optional[TradeLogger] = None,
        monitor: Optional[Monitor] = None,
    ) -> None:
        """
        Initialize RiskEngine.

        Args:
            config: TradingConfig object.
            account_balance: Current account balance.
            logger_db: Optional TradeLogger instance.
            monitor: Optional Monitor instance.
        """
        self.cfg = config
        self.balance = account_balance
        self.peak_equity = account_balance
        self.daily = DailyRiskStats(peak_equity=account_balance)
        self.open_positions: Dict[str, int] = {}  # symbol -> ticket
        self.trade_logger = logger_db
        self.monitor = monitor
        logger.info("RiskEngine initialised | balance=%.2f", account_balance)

    def approve(self, signal: TradeSignal, signal_id: Optional[int] = None) -> bool:
        """
        Run the full institutional risk filter cascade.
        Returns True only if ALL layers pass.

        Args:
            signal: TradeSignal to validate.
            signal_id: Optional ID for logging purposes.

        Returns:
            bool: True if approved, False otherwise.
        """
        rejection_reason = self._get_rejection_reason(signal)

        if rejection_reason:
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
            return False

        return True

    def _get_rejection_reason(self, signal: TradeSignal) -> Optional[str]:
        """Check all risk layers and return first rejection reason."""
        # 1. Circuit Breakers (Drawdown)
        if not self._check_drawdown_circuit_breaker():
            return "Equity drawdown circuit breaker"

        # 2. Daily Loss Limits (Level 4/Emergency Stop)
        if not self._check_daily_loss_limit():
            return "Daily loss limit exceeded"

        # 3. Daily Trade Limits
        if self.daily.trade_count >= self.cfg.max_daily_trades:
            return f"Max daily trades ({self.cfg.max_daily_trades}) reached"

        if self.daily.consecutive_losses >= 3:
            return "Halt trading after 3 consecutive losses"

        # 4. Position Limits
        if len(self.open_positions) >= self.cfg.max_positions:
            return f"Max concurrent positions ({self.cfg.max_positions}) reached"

        # 5. Signal Validation
        if signal.confidence < self.cfg.min_confidence:
            return f"Confidence {signal.confidence:.2f} < {self.cfg.min_confidence}"

        # 6. Risk Per Trade Validation
        # Assuming Gold contract size 100 for risk calc
        contract_size = 100 if "XAU" in signal.symbol else 1
        risk_amount = (
            abs(signal.entry_price - signal.stop_loss) * signal.lot_size * contract_size
        )
        risk_pct = risk_amount / self.balance
        if risk_pct > self.cfg.risk_per_trade * 1.1:  # Allow 10% buffer for rounding
            return f"Risk per trade {risk_pct*100:.2f}% exceeds limit {self.cfg.risk_per_trade*100:.2f}%"

        return None

    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        atr: float,
        avg_atr: float,
    ) -> float:
        """
        Calculate lot size based on 1% risk rule and ATR volatility thresholds.
        Implementation of Section 1.3 and Section 5.1 of RISK_LIMITS.md.

        Args:
            symbol: Trading symbol.
            entry_price: Planned entry price.
            stop_loss: Planned stop loss price.
            atr: Current 14-period ATR.
            avg_atr: 30-day average ATR.

        Returns:
            float: Calculated lot size in lots.
        """
        # Risk capital based on account balance
        risk_capital = self.balance * self.cfg.risk_per_trade

        # Volatility multiplier (Section 5.1)
        vol_multiplier = 1.0
        atr_ratio = atr / avg_atr if avg_atr > 0 else 1.0

        if atr_ratio > 3.0:
            logger.critical("EXTREME VOLATILITY (>3x normal) - HALT TRADING")
            return 0.0
        elif atr_ratio > 2.0:
            vol_multiplier = 0.50
        elif atr_ratio > 1.5:
            vol_multiplier = 0.75

        # Cascading Daily Loss adjustment (Section 2.1)
        loss_multiplier = self._get_daily_loss_multiplier()

        # Equity Drawdown adjustment (Section 6.1)
        dd_multiplier = self._get_drawdown_multiplier()

        effective_multiplier = vol_multiplier * loss_multiplier * dd_multiplier

        # Calculate lot size based on price risk
        risk_per_lot_points = abs(entry_price - stop_loss)
        if risk_per_lot_points == 0:
            return 0.0

        # Assuming Gold contract size 100
        contract_size = 100 if "XAU" in symbol else 1
        lot_size = (risk_capital * effective_multiplier) / (
            risk_per_lot_points * contract_size
        )

        # Apply constraints (Section 1.1)
        lot_size = max(0.01, round(lot_size, 2))

        # Max position size 10% of equity (Section 1.1)
        max_notional = self.balance * 0.10
        notional_value = lot_size * entry_price * contract_size
        if notional_value > max_notional:
            lot_size = round(max_notional / (entry_price * contract_size), 2)

        return max(0.01, lot_size)

    def _get_daily_loss_multiplier(self) -> float:
        """Section 2.1: Cascading daily loss logic."""
        if self.daily.peak_equity <= 0:
            return 1.0
        # Use abs(realised_pnl) because realised_pnl is negative for losses
        loss_pct = abs(min(0, self.daily.realised_pnl)) / self.daily.peak_equity

        if loss_pct >= self.cfg.daily_loss_lvl3:  # 4%
            return 0.25
        if loss_pct >= self.cfg.daily_loss_lvl2:  # 3%
            return 0.50
        return 1.0

    def _get_drawdown_multiplier(self) -> float:
        """Section 6.1: Equity drawdown protection."""
        if self.peak_equity <= 0:
            return 1.0
        drawdown = (self.peak_equity - self.balance) / self.peak_equity
        if drawdown >= self.cfg.drawdown_lvl3:  # 20%
            return 0.50
        if drawdown >= self.cfg.drawdown_lvl2:  # 15%
            return 0.75
        return 1.0

    def _check_drawdown_circuit_breaker(self) -> bool:
        """Section 6.1: Level 4/5 Drawdown stops."""
        if self.peak_equity <= 0:
            return True
        drawdown = (self.peak_equity - self.balance) / self.peak_equity
        if drawdown >= self.cfg.drawdown_lvl5:  # 30%
            logger.critical("CIRCUIT BREAKER: 30%% Drawdown reached. FORCE CLOSE ALL.")
            if self.monitor:
                self.monitor.alert_circuit_breaker(drawdown)
            return False
        if drawdown >= self.cfg.drawdown_lvl4:  # 25%
            logger.warning("Drawdown Level 4 (25%%) reached. Halt new positions.")
            return False
        return True

    def _check_daily_loss_limit(self) -> bool:
        """Section 2.1: Level 4 Daily loss stop."""
        if self.daily.peak_equity <= 0:
            return True
        loss_pct = abs(min(0, self.daily.realised_pnl)) / self.daily.peak_equity
        if loss_pct >= self.cfg.daily_loss_lvl4:  # 5%
            logger.warning("Daily loss Level 4 (5%%) reached. HALT ALL TRADING.")
            return False
        return True

    def update_equity(self, current_equity: float) -> None:
        """Update peak equity and current balance."""
        self.balance = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        if current_equity > self.daily.peak_equity:
            self.daily.peak_equity = current_equity

    def record_trade_result(self, pnl: float) -> None:
        """Record outcome of a closed trade."""
        self.daily.realised_pnl += pnl
        self.daily.trade_count += 1
        if pnl < 0:
            self.daily.consecutive_losses += 1
        else:
            self.daily.consecutive_losses = 0

    def reset_daily(self) -> None:
        """Start of day reset."""
        if self.monitor:
            self.monitor.send_daily_summary(
                self.daily.realised_pnl, self.daily.trade_count
            )
        self.daily = DailyRiskStats(peak_equity=self.balance)
        logger.info("Daily risk stats reset")


__all__ = ["RiskEngine", "TradeSignal", "DailyRiskStats"]
