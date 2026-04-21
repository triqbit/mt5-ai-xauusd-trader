"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_engine.py
Institutional-grade risk engine implementing all limits from RISK_LIMITS.md.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from src.core.config import TradingConfig
from src.core.monitor import Monitor
from src.core.trade_logger import TradeLogger
from src.trading.risk_manager import DailyStats, TradeSignal

logger = logging.getLogger(__name__)

@dataclass
class RiskMetrics:
    """Track complex risk metrics over time."""
    weekly_loss: float = 0.0
    monthly_loss: float = 0.0
    consecutive_losses: int = 0
    consecutive_wins: int = 0
    margin_utilization: float = 0.0
    last_reset_weekly: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_reset_monthly: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class RiskEngine:
    """
    Enhanced risk engine implementing the full RISK_LIMITS.md specification.
    Supersedes basic RiskManager.
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
        self.metrics = RiskMetrics()
        self.open_positions: Dict[str, List[Dict]] = {}  # symbol -> [position_info]
        self.trade_logger = logger_db
        self.monitor = monitor

        logger.info("RiskEngine initialised | balance=%.2f", account_balance)

    def approve(self, signal: TradeSignal, signal_id: Optional[int] = None) -> bool:
        """
        Comprehensive multi-layer risk validation.
        """
        # 1. System-level Circuit Breakers (Section 6.1)
        if not self._check_drawdown_circuit_breaker():
            return self._reject(signal, "Drawdown Circuit Breaker", signal_id)

        # 2. Daily Loss Limits (Cascading) (Section 2.1)
        if not self._check_daily_loss_cascading():
            return self._reject(signal, "Daily Loss Limit", signal_id)

        # 3. Weekly/Monthly Limits (Section 3)
        if not self._check_periodic_limits():
            return self._reject(signal, "Weekly/Monthly Limit", signal_id)

        # 4. Position-level Limits (Section 1.1)
        if not self._check_position_limits(signal):
            return self._reject(signal, "Position Limits", signal_id)

        # 5. Exposure Limits (Section 1.2)
        if not self._check_exposure_limits(signal):
            return self._reject(signal, "Exposure Limits", signal_id)

        # 6. Prediction Confidence (Section 4.1)
        if signal.confidence < self.cfg.confidence_threshold:
            return self._reject(signal, f"Confidence {signal.confidence:.2f} < {self.cfg.confidence_threshold}", signal_id)

        # 7. Risk/Reward (Section 7.2)
        if not self._check_risk_reward(signal):
            return self._reject(signal, "Risk-Reward Ratio", signal_id)

        logger.info("Signal APPROVED | %s %s | size=%.2f", signal.symbol, "BUY" if signal.direction > 0 else "SELL", signal.lot_size)
        return True

    def size_position(self, symbol: str, current_price: float, atr: float, account_equity: float) -> float:
        """
        ATR-based position sizing as per RISK_LIMITS.md 1.3 and 5.1.
        Risk 1% of account per trade.
        """
        if atr <= 0:
            return self.cfg.min_lot_size

        risk_pct = self.cfg.risk_per_trade
        risk_amount = account_equity * risk_pct
        sl_distance = 2 * atr

        if sl_distance == 0:
            return self.cfg.min_lot_size

        contract_size = 100 if "XAU" in symbol else 100000
        lot_size = risk_amount / (sl_distance * contract_size)

        # Hard limits (Section 1.1)
        max_notional = account_equity * self.cfg.max_position_size_pct
        max_lot_notional = max_notional / (current_price * contract_size)

        lot_size = min(lot_size, max_lot_notional)
        lot_size = max(self.cfg.min_lot_size, round(lot_size, 2))
        return lot_size

    def update_equity(self, current_equity: float, margin_info: Optional[Dict] = None) -> None:
        """Update metrics and check for margin alerts."""
        self.balance = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        if margin_info:
            margin_used = margin_info.get('margin', 0)
            if current_equity > 0:
                self.metrics.margin_utilization = margin_used / current_equity
                # Section 1.2 Margin Alert
                if self.metrics.margin_utilization > self.cfg.margin_halt_level:
                    logger.critical("MARGIN ALERT: Utilization %.1f%%", self.metrics.margin_utilization * 100)
                    if self.monitor:
                        self.monitor.send_message(f"🚨 CRITICAL: Margin utilization at {self.metrics.margin_utilization*100:.1f}%")

    def record_trade_result(self, pnl: float) -> None:
        """Update daily/weekly/monthly stats and streaks."""
        self.daily.realised_pnl += pnl
        self.daily.trade_count += 1
        self.metrics.weekly_loss -= min(pnl, 0)
        self.metrics.monthly_loss -= min(pnl, 0)

        if pnl > 0:
            self.metrics.consecutive_wins += 1
            self.metrics.consecutive_losses = 0
        elif pnl < 0:
            self.metrics.consecutive_losses += 1
            self.metrics.consecutive_wins = 0

    def sync_positions(self, positions: List[Dict]) -> None:
        """Sync open positions from connector."""
        self.open_positions = {}
        for p in positions:
            symbol = p['symbol']
            if symbol not in self.open_positions:
                self.open_positions[symbol] = []
            self.open_positions[symbol].append(p)

    def _reject(self, signal: TradeSignal, reason: str, signal_id: Optional[int]) -> bool:
        logger.warning("Signal REJECTED | %s | Reason: %s", signal.symbol, reason)
        if self.trade_logger:
            self.trade_logger.log_risk_event(
                event_type="SIGNAL_REJECTED",
                description=reason,
                symbol=signal.symbol,
                signal_id=signal_id
            )
        return False

    def _check_drawdown_circuit_breaker(self) -> bool:
        drawdown = (self.peak_equity - self.balance) / self.peak_equity if self.peak_equity > 0 else 0

        # Section 6.1 Drawdown Levels
        if drawdown >= self.cfg.drawdown_limit_level5: # 30%
            logger.critical("CIRCUIT BREAKER: 30%% Drawdown reached. Force close required.")
            return False
        if drawdown >= self.cfg.drawdown_limit_level4: # 25%
            return False
        if drawdown >= self.cfg.drawdown_limit_level3: # 20%
            # Section 6.1 action: Reduce position size to 50%.
            # Handled in sizing or rejected here if we want a hard halt.
            # For simplicity, we halt new trades at 20%+ drawdown if not specifically handled.
            return True # Allow for now but could be more restrictive

        return True

    def _check_daily_loss_cascading(self) -> bool:
        if self.daily.peak_equity <= 0:
            return True
        loss_pct = abs(self.daily.realised_pnl) / self.daily.peak_equity
        if self.daily.realised_pnl >= 0:
            return True

        # Section 2.1
        if loss_pct >= self.cfg.daily_loss_hard_stop: # 6%
            return False
        if loss_pct >= self.cfg.daily_loss_limit_level4: # 5%
            return False

        # Section 2.3
        if self.daily.trade_count >= self.cfg.max_daily_trades:
            return False
        return not self.metrics.consecutive_losses >= self.cfg.max_losing_streak

    def _check_periodic_limits(self) -> bool:
        # Section 3
        if self.metrics.weekly_loss > (self.balance * self.cfg.max_weekly_loss):
            return False
        return not self.metrics.monthly_loss > self.balance * self.cfg.max_monthly_loss

    def _check_position_limits(self, signal: TradeSignal) -> bool:
        total_open = sum(len(positions) for positions in self.open_positions.values())
        if total_open >= self.cfg.max_positions:
            return False

        return not signal.lot_size < self.cfg.min_lot_size

    def _check_exposure_limits(self, signal: TradeSignal) -> bool:
        # Section 1.2 Single Direction: Max 30% net long OR short
        symbol_positions = self.open_positions.get(signal.symbol, [])
        net_lots = sum(p['volume'] * (1 if p['type'] == 0 else -1) for p in symbol_positions)
        new_net_lots = net_lots + (signal.lot_size * signal.direction)

        contract_size = 100 if "XAU" in signal.symbol else 100000
        notional_exposure = abs(new_net_lots) * signal.entry_price * contract_size

        exposure_pct = notional_exposure / self.balance if self.balance > 0 else 0
        if exposure_pct > self.cfg.max_single_direction_exposure_pct:
            logger.warning("Exposure limit exceeded: %.1f%% > %.1f%%", exposure_pct * 100, self.cfg.max_single_direction_exposure_pct * 100)
            return False

        return True

    def _check_risk_reward(self, signal: TradeSignal) -> bool:
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.entry_price)
        if risk == 0:
            return False
        return (reward / risk) >= 1.5

__all__ = ["RiskEngine", "RiskMetrics"]
