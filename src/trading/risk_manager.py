"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_manager.py

Enterprise risk management engine implementing:
  - ATR-based position sizing (14-period vs 30-day average)
  - Cascading daily loss circuit breakers (Level 1-4)
  - Drawdown safeguards and exposure limits
  - 8-layer safety cascade signal validation
  - Audit-logged decision chain

This module is the single source of truth for risk management, harmonizing
the previously fragmented RiskEngine and RiskManager modules.

Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

import pandas as pd

from src.core.audit_log import get_audit_logger
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


class AuditedRiskManager:
    """
    Institutional risk engine with integrated audit logging.
    Enforces RISK_LIMITS.md safeguards via an 8-layer cascade.
    """

    def __init__(
        self,
        config: TradingConfig,
        account_balance: float,
        logger_db: Optional[TradeLogger] = None,
        monitor: Optional[Monitor] = None,
    ) -> None:
        """
        Initialize the AuditedRiskManager.

        Args:
            config: System configuration.
            account_balance: Initial account balance.
            logger_db: Optional logger for risk events.
            monitor: Optional monitor for alerts.
        """
        self.cfg = config
        self.balance = account_balance
        self.peak_equity = account_balance
        self.daily = DailyStats(peak_equity=account_balance)
        self.open_positions: Dict[str, int] = {}  # symbol -> ticket
        self.trade_logger = logger_db
        self.monitor = monitor
        logger.info("AuditedRiskManager initialised | balance=%.2f", account_balance)

    # -- Public API ---------------------------------------------------------

    def approve(
        self,
        signal: TradeSignal,
        market_data: Optional[pd.DataFrame] = None,
        open_positions: Optional[List[Dict[str, Any]]] = None,
        model_health: Optional[Dict[str, float]] = None,
        signal_id: Optional[int] = None,
    ) -> bool:
        """
        Legacy approve method wrapper for backward compatibility with main.py loop.
        Returns True if the signal is approved by the 8-layer cascade.
        """
        decision = self.validate_signal(
            signal=signal,
            market_data=market_data,
            open_positions=open_positions,
            model_health=model_health,
        )

        if not decision.is_approved:
            logger.warning(
                "Signal REJECTED | %s %s | Reason: %s",
                signal.symbol,
                signal.direction,
                decision.reason,
            )
            if self.trade_logger:
                self.trade_logger.log_risk_event(
                    event_type="SIGNAL_REJECTED",
                    description=decision.reason,
                    symbol=signal.symbol,
                    signal_id=signal_id,
                )
        return decision.is_approved

    def validate_signal(
        self,
        signal: TradeSignal,
        market_data: Optional[pd.DataFrame] = None,
        open_positions: Optional[List[Dict[str, Any]]] = None,
        model_health: Optional[Dict[str, float]] = None,
    ) -> RiskDecision:
        """
        Validate a trade signal against the 8-layer cascade from RISK_LIMITS.md.

        Layers:
          1. Circuit Breakers (Equity Drawdown).
          2. Daily Loss Limits (Emergency Stop).
          3. Activity Limits (Max Daily Trades, Max Consecutive Losses).
          4. Exposure Limits (Max Concurrent Positions, Total Notional).
          5. Symbol Allocation (Approved Portfolio).
          6. Prediction Limits (Min Confidence).
          7. Risk-Reward Validation (Institutional R:R ratio).
          8. Model Health (Drift, Accuracy, Calibration).

        Returns:
            RiskDecision: Approval status, reason, and adjusted lot size.
        """
        decision_chain = {
            "circuit_breaker": self._check_drawdown_breaker(),
            "daily_loss": self.get_daily_loss_level() < 4,
            "activity_limits": self._check_activity_limits(),
            "exposure_limits": self._check_exposure_limits(signal, open_positions, market_data),
            "symbol_allocation": self._check_symbol_allocation(signal.symbol),
            "min_confidence": signal.confidence >= self.cfg.min_confidence,
            "risk_reward": self._check_risk_reward(signal),
            "model_health": self._check_model_health(model_health),
        }

        is_approved = all(decision_chain.values())
        rejection_reason = ""
        if not is_approved:
            failed_layers = [k for k, v in decision_chain.items() if not v]
            rejection_reason = f"Failed: {', '.join(failed_layers)}"

        # Calculate adjusted lot size
        adjusted_lots = 0.0
        if is_approved:
            adjusted_lots = self.calculate_position_size(signal.symbol, market_data)
            if adjusted_lots < self.cfg.min_lot_size:
                is_approved = False
                rejection_reason = f"Calculated lot size {adjusted_lots} below minimum"
                decision_chain["lot_sizing"] = False

        # Log to Audit Trail
        try:
            audit = get_audit_logger()
            audit.log_risk_decision(
                symbol=signal.symbol,
                direction=signal.direction,
                decision_chain=decision_chain,
                passed=is_approved,
            )

            # Escalation logging
            if not decision_chain.get("circuit_breaker", True):
                audit.log_operator_action(
                    operator="system",
                    action="circuit_breaker_triggered",
                    reason=f"Hard drawdown limit hit during validation for {signal.symbol}",
                    metadata={"symbol": signal.symbol, "decision_chain": decision_chain},
                )
            if not decision_chain.get("daily_loss", True):
                audit.log_operator_action(
                    operator="system",
                    action="daily_loss_limit_triggered",
                    reason=f"Daily loss limit reached during validation for {signal.symbol}",
                    metadata={"symbol": signal.symbol, "decision_chain": decision_chain},
                )

        except (RuntimeError, ImportError):
            pass

        if not is_approved and self.monitor:
            failed_layers = [k for k, v in decision_chain.items() if not v]
            for layer in failed_layers:
                self.monitor.record_internal_rejection("risk_manager", layer.upper())

        return RiskDecision(
            is_approved=is_approved,
            reason=rejection_reason,
            adjusted_lot_size=adjusted_lots,
            trace=decision_chain,
        )

    def calculate_position_size(self, symbol: str, market_data: Optional[pd.DataFrame]) -> float:
        """
        ATR-based position sizing according to RISK_LIMITS.md.
        """
        if market_data is None or market_data.empty or "atr" not in market_data.columns:
            # Fallback to standard risk-based sizing if ATR is missing
            risk_capital = self.balance * self.cfg.risk_per_trade
            # Standard lot for XAUUSD is 100oz. If we assume a generic stop of 2.0 pips.
            # This is a very rough fallback.
            return max(self.cfg.min_lot_size, round(risk_capital / 200.0, 2))

        current_atr = market_data["atr"].iloc[-1]
        # Approx 30 days of M5 bars if available, else all data
        window = min(len(market_data), 8640)
        avg_atr = market_data["atr"].tail(window).mean()

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

        # Sizing: risk X% (cfg.risk_per_trade) of balance
        risk_amount = self.balance * self.cfg.risk_per_trade

        # ATR * 100 converts gold ATR to $ per lot (1.0 ATR move = $100 per lot)
        # Note: This is specific to Gold (XAUUSD) 100 contract size.
        lot_size = (risk_amount / (current_atr * 100)) * total_multiplier

        # Cap at Max Position Size (e.g. 10% of equity)
        max_notional = self.balance * getattr(self.cfg, "max_position_size_pct", 0.10)
        price = market_data["close"].iloc[-1]
        max_lots = max_notional / (price * 100)

        final_lots = min(lot_size, max_lots)
        final_lots = max(self.cfg.min_lot_size, round(final_lots, 2))

        return final_lots

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
        Provided for compatibility and specific strategy needs.
        """
        if avg_loss == 0:
            return self.cfg.min_lot_size
        kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        kelly_fraction = max(0.0, min(kelly_fraction, 0.25))  # cap at 25% Kelly
        risk_capital = self.balance * self.cfg.risk_per_trade
        lot_size = (risk_capital * kelly_fraction) / (avg_loss * pip_value)
        lot_size = max(self.cfg.min_lot_size, round(lot_size, 2))
        return lot_size

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
        if loss_pct >= self.cfg.max_daily_loss: return 4
        if loss_pct >= getattr(self.cfg, "daily_loss_lvl3", 0.04): return 3
        if loss_pct >= getattr(self.cfg, "daily_loss_lvl2", 0.03): return 2
        if loss_pct >= getattr(self.cfg, "daily_loss_lvl1", 0.02): return 1
        return 0

    def _check_activity_limits(self) -> bool:
        """Layer 3: Max trades and consecutive losses."""
        if self.daily.trade_count >= getattr(self.cfg, "max_trades_per_day", 20):
            return False
        if self.daily.consecutive_losses >= self.cfg.max_losing_streak:
            return False
        return True

    def _check_exposure_limits(
        self,
        signal: TradeSignal,
        open_positions: Optional[List[Dict[str, Any]]],
        market_data: Optional[pd.DataFrame]
    ) -> bool:
        """Layer 4: Max concurrent positions and notional limits."""
        positions = open_positions or []
        if len(positions) >= self.cfg.max_positions:
            return False

        # Total notional check
        total_lots = sum(pos.get("volume", 0.0) for pos in positions) + self.cfg.min_lot_size
        price = market_data["close"].iloc[-1] if market_data is not None and not market_data.empty else 2300.0
        total_notional = total_lots * price * 100
        max_notional_pct = getattr(self.cfg, "max_total_notional_pct", 1.0)
        if total_notional > (self.balance * max_notional_pct):
            return False

        return True

    def _check_symbol_allocation(self, symbol: str) -> bool:
        """Layer 5: Symbol check."""
        return symbol in ALLOCATION_WEIGHTS

    def _check_risk_reward(self, signal: TradeSignal, min_rr: float = 1.5) -> bool:
        """Layer 7: Risk-Reward validation."""
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
        if health.get("calibration", 0.0) > self.cfg.model_calibration_threshold:
            return False
        return True

    def get_size_multiplier_from_loss(self) -> float:
        """Multiplier based on daily loss level."""
        level = self.get_daily_loss_level()
        mapping = {0: 1.0, 1: 1.0, 2: 0.5, 3: 0.25, 4: 0.0}
        return mapping.get(level, 0.0)


# Type alias for RiskManager to prevent breaking imports immediately
RiskManager = AuditedRiskManager

__all__ = ["ALLOCATION_WEIGHTS", "DailyStats", "AuditedRiskManager", "RiskManager"]
