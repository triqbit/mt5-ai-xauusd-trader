"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_manager.py

Enterprise risk management engine implementing:
  - ATR-based position sizing (14-period vs 30-day average)
  - Cascading daily loss circuit breakers (Level 1-4)
  - Drawdown safeguards and exposure limits
  - 8-layer safety cascade signal validation

This module relies on the unified TradeSignal schema from src.core.schemas
to ensure all signals entering the risk engine are technically valid.

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
    Central risk authority.
    Enforces RISK_LIMITS.md safeguards via an 8-layer cascade.
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
        Returns a RiskDecision object containing approval status and adjusted lot size.
        """
        trace = {
            "circuit_breaker": self._check_circuit_breaker(),
            "daily_loss": self.get_daily_loss_level() < 4,
            "activity_limits": self._check_activity_limits(),
            "exposure_limits": self._check_exposure_limits(signal, open_positions, market_data),
            "symbol_allocation": self._check_symbol_allocation(signal.symbol),
            "min_confidence": self._check_minimum_confidence(signal.confidence),
            "risk_reward": self._check_risk_reward(signal),
            "model_health": self._check_model_health(model_health),
        }

        passed = all(trace.values())
        reason = "Approved" if passed else self._get_rejection_reason(trace)

        adjusted_lots = 0.0
        if passed:
            adjusted_lots = self.calculate_position_size(signal.symbol, market_data)
            if adjusted_lots < self.cfg.min_lot_size:
                passed = False
                reason = f"Calculated lot size {adjusted_lots} below minimum"
                trace["position_sizing"] = False

        decision = RiskDecision(
            is_approved=passed,
            reason=reason,
            adjusted_lot_size=adjusted_lots,
            trace=trace
        )

        if not passed:
            logger.warning(
                "Signal REJECTED | %s %s | Reason: %s",
                signal.symbol,
                signal.direction,
                reason,
            )
            if self.trade_logger:
                self.trade_logger.log_risk_event(
                    event_type="SIGNAL_REJECTED",
                    description=reason,
                    symbol=signal.symbol,
                    signal_id=signal_id,
                )

        return decision

    def calculate_position_size(self, symbol: str, market_data: pd.DataFrame) -> float:
        """
        ATR-based position sizing according to RISK_LIMITS.md.
        """
        if market_data.empty or "atr" not in market_data.columns:
            return self.cfg.min_lot_size

        current_atr = market_data["atr"].iloc[-1]
        # Approx 30 days of M5 if timeframe is M5, but we use tail(8640) as heuristic
        avg_atr = market_data["atr"].tail(8640).mean()

        vol_multiplier = 1.0
        ratio = current_atr / avg_atr if avg_atr > 0 else 1.0

        if ratio > getattr(self.cfg, "volatility_extreme_threshold", 3.0):
            return 0.0
        elif ratio > getattr(self.cfg, "volatility_very_high_threshold", 2.0):
            vol_multiplier = 0.5
        elif ratio > getattr(self.cfg, "volatility_high_threshold", 1.5):
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
        max_notional_pct = getattr(self.cfg, "max_position_size_pct", 0.1)
        max_notional = self.balance * max_notional_pct
        price = market_data["close"].iloc[-1]
        max_lots = max_notional / (price * 100)

        final_lots = min(lot_size, max_lots)
        final_lots = max(self.cfg.min_lot_size, round(final_lots, 2))

        return final_lots

    def update_equity(self, current_equity: float, realized_pnl: float = 0) -> None:
        """Call after every closed trade or on heartbeat."""
        self.balance = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        if realized_pnl != 0:
            self.daily.realised_pnl += realized_pnl
            self.daily.trade_count += 1
            if realized_pnl < 0:
                self.daily.consecutive_losses += 1
            else:
                self.daily.consecutive_losses = 0

        if current_equity > self.daily.peak_equity:
            self.daily.peak_equity = current_equity

    def record_pnl(self, pnl: float) -> None:
        """Accumulate intraday realised PnL."""
        self.update_equity(self.balance, pnl)

    def reset_daily(self) -> None:
        """Must be called at the start of each trading day."""
        if self.monitor:
            self.monitor.send_daily_summary(self.daily.realised_pnl, self.daily.trade_count)
        self.daily = DailyStats(peak_equity=self.balance)
        logger.info("Daily stats reset")

    def get_daily_loss_level(self) -> int:
        """
        Daily Loss Level (0-4).
        """
        if self.daily.peak_equity <= 0 or self.daily.realised_pnl >= 0:
            return 0

        loss_pct = abs(self.daily.realised_pnl) / self.daily.peak_equity

        if loss_pct >= self.cfg.max_daily_loss:
            return 4
        if loss_pct >= getattr(self.cfg, "daily_loss_lvl3", 0.05):
            return 3
        if loss_pct >= getattr(self.cfg, "daily_loss_lvl2", 0.03):
            return 2
        if loss_pct >= getattr(self.cfg, "daily_loss_lvl1", 0.01):
            return 1
        return 0

    def get_size_multiplier_from_loss(self) -> float:
        """Multiplier based on daily loss level."""
        level = self.get_daily_loss_level()
        mapping = {0: 1.0, 1: 1.0, 2: 0.5, 3: 0.25, 4: 0.0}
        return mapping.get(level, 0.0)

    # -- Private filter layers ----------------------------------------------
    def _get_rejection_reason(self, trace: Dict[str, bool]) -> str:
        failed = [k for k, v in trace.items() if not v]
        return f"Failed filters: {', '.join(failed)}"

    def _check_activity_limits(self) -> bool:
        if self.daily.trade_count >= getattr(self.cfg, "max_trades_per_day", 50):
            return False
        if self.daily.consecutive_losses >= self.cfg.max_losing_streak:
            return False
        return True

    def _check_exposure_limits(
        self, signal: TradeSignal, open_positions: List[Dict[str, Any]], market_data: pd.DataFrame
    ) -> bool:
        if len(open_positions) >= self.cfg.max_positions:
            return False

        # 30% net directional exposure
        net_lots = 0.0
        for pos in open_positions:
            vol = pos.get("volume", pos.get("lot_size", 0.0))
            # type 0 is BUY, type 1 is SELL in MT5
            pos_type = pos.get("type", 0)
            if pos_type == 0:
                net_lots += vol
            else:
                net_lots -= vol

        net_lots += self.cfg.min_lot_size if signal.direction > 0 else -self.cfg.min_lot_size
        price_estimate = market_data["close"].iloc[-1] if not market_data.empty else 2300.0
        notional = abs(net_lots) * price_estimate * 100
        exposure_pct = notional / self.balance if self.balance > 0 else 1.0

        max_dir_pct = getattr(self.cfg, "max_single_direction_pct", 0.3)
        if exposure_pct > max_dir_pct:
            return False

        # Total notional < 100% equity (or whatever is in config)
        total_lots = sum(pos.get("volume", pos.get("lot_size", 0.0)) for pos in open_positions) + self.cfg.min_lot_size
        total_notional = total_lots * price_estimate * 100
        max_total_notional_pct = getattr(self.cfg, "max_total_notional_pct", 1.0)
        if total_notional > (self.balance * max_total_notional_pct):
            return False

        return True

    def _check_model_health(self, health: Optional[dict]) -> bool:
        if health is None:
            return True

        drift = float(health.get("drift", 0.0))
        accuracy = float(health.get("accuracy", 1.0))
        calibration = float(health.get("calibration", 0.0))

        if drift > self.cfg.model_drift_threshold:
            return False
        if accuracy < self.cfg.model_accuracy_floor:
            return False
        if calibration > self.cfg.model_calibration_threshold:
            return False

        return True

    def _check_circuit_breaker(self) -> bool:
        drawdown = (self.peak_equity - self.balance) / self.peak_equity
        if drawdown >= self.cfg.max_drawdown:
            logger.critical(
                "CIRCUIT BREAKER: drawdown=%.1f%% - trading halted",
                drawdown * 100,
            )
            if self.trade_logger:
                self.trade_logger.log_risk_event(
                    event_type="CIRCUIT_BREAKER",
                    description=f"Drawdown {drawdown * 100:.1f}% hit {self.cfg.max_drawdown*100}% limit",
                )
            if self.monitor:
                self.monitor.alert_circuit_breaker(drawdown)
            return False
        return True

    def _check_symbol_allocation(self, symbol: str) -> bool:
        """Block trading on symbols not in the All-Weather portfolio."""
        if symbol not in ALLOCATION_WEIGHTS:
            logger.warning("Symbol %s not in approved portfolio", symbol)
            return False
        return True

    def _check_minimum_confidence(self, confidence: float) -> bool:
        if confidence < self.cfg.min_confidence:
            return False
        return True

    def _check_risk_reward(self, signal: TradeSignal) -> bool:
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.entry_price)
        if risk == 0:
            return False
        rr = reward / risk
        min_rr = getattr(self.cfg, "min_risk_reward", 1.5)
        if rr < min_rr:
            return False
        return True


__all__ = ["ALLOCATION_WEIGHTS", "DailyStats", "RiskManager"]
