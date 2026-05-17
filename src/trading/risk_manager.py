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
class RiskDecision:
    """Decision details from the RiskManager."""

    is_approved: bool
    reason: str = ""
    adjusted_lot_size: float = 0.0


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
    Every signal must be approved here before reaching the order router.
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
        self.open_positions: Dict[str, int] = {}  # symbol -> ticket
        self.trade_logger = logger_db
        self.monitor = monitor
        logger.info("RiskManager initialised | balance=%.2f", account_balance)

    # -- Public API ---------------------------------------------------------

    def validate_signal(
        self,
        signal: TradeSignal,
        market_data: pd.DataFrame,
        open_positions: List[Dict[str, Any]],
        model_health: Optional[Dict[str, float]] = None,
    ) -> RiskDecision:
        """
        Validate a trade signal against the 8-layer cascade.

        Layers:
          1. Circuit Breakers (Equity Drawdown).
          2. Daily Loss Limits (Level 4 Emergency Stop).
          3. Activity Limits (Max Daily Trades, Max Consecutive Losses).
          4. Exposure Limits (Max Concurrent Positions, Single Direction, Total Notional).
          5. Symbol Allocation (Approved Portfolio).
          6. Prediction Limits (Min Confidence).
          7. Risk-Reward Validation (Institutional R:R ratio).
          8. Model Health (Drift, Accuracy, Calibration).
        """
        # Layer 1: Circuit Breakers (Equity Drawdown)
        if not self._check_circuit_breaker():
            return RiskDecision(False, "Hard drawdown limit reached")

        # Layer 2: Daily Loss Limits (Level 4)
        if self.get_daily_loss_level() >= 4:
            return RiskDecision(False, "Daily loss limit reached (Level 4)")

        # Layer 3: Activity Limits
        if self.daily.trade_count >= self.cfg.max_trades_per_day:
            return RiskDecision(False, "Max daily trades reached")
        if self.daily.consecutive_losses >= self.cfg.max_losing_streak:
            return RiskDecision(False, "Max consecutive losses reached")

        # Layer 4: Exposure Limits
        if len(open_positions) >= self.cfg.max_positions:
            return RiskDecision(False, "Max concurrent positions reached")
        if not self._check_directional_exposure(signal, open_positions):
            return RiskDecision(False, "Max directional exposure reached (30%)")
        if not self._check_total_notional(signal, open_positions, market_data):
            return RiskDecision(False, "Total notional exposure exceeds equity")

        # Layer 5: Symbol Allocation
        if not self._check_symbol_allocation(signal.symbol):
            return RiskDecision(False, f"Symbol {signal.symbol} not in approved list")

        # Layer 6: Prediction Limits
        if signal.confidence < self.cfg.min_confidence:
            return RiskDecision(
                False, f"Confidence {signal.confidence:.2f} below {self.cfg.min_confidence}"
            )

        # Layer 7: Risk-Reward Validation (Min 1.5 R:R)
        if not self._check_risk_reward(signal):
            return RiskDecision(False, "Risk-Reward ratio below 1.5")

        # Layer 8: Model Health
        if not self._check_model_health(model_health):
            return RiskDecision(False, "Model health metrics below threshold")

        # Calculate final lot size using ATR-based sizing
        adjusted_lots = self.calculate_position_size(signal.symbol, market_data)

        if adjusted_lots < self.cfg.min_lot_size:
            return RiskDecision(False, f"Calculated lot size {adjusted_lots} below minimum")

        return RiskDecision(True, "Approved", adjusted_lots)

    def approve(
        self,
        signal: TradeSignal,
        signal_id: Optional[int] = None,
        model_health: Optional[dict] = None,
    ) -> bool:
        """
        Legacy approve method. Redirects to validate_signal with empty context.
        DEPRECATED: Use validate_signal instead.
        """
        # We don't have market_data or open_positions here in the legacy signature.
        # This is why we are harmonizing.
        # For backward compatibility, we'll try to provide minimal context or just fail if needed.
        # In main.py we will update the call.
        logger.warning("RiskManager.approve() is deprecated. Use validate_signal() instead.")
        # Minimal mock for market data if we really need to support this legacy call
        mock_data = pd.DataFrame({"close": [signal.entry_price], "atr": [0.1]})
        decision = self.validate_signal(signal, mock_data, [], model_health)
        return decision.is_approved

    def calculate_position_size(self, symbol: str, market_data: pd.DataFrame) -> float:
        """
        ATR-based position sizing according to RISK_LIMITS.md.
        """
        # Try to find ATR column (could be 'atr' or 'base_M5_atr' etc)
        atr_col = "atr"
        if "atr" not in market_data.columns:
            for col in market_data.columns:
                if "atr" in col.lower():
                    atr_col = col
                    break

        if market_data.empty or atr_col not in market_data.columns:
            return self.cfg.min_lot_size

        current_atr = market_data[atr_col].iloc[-1]
        # Approx 30 days of M5 is ~8640 bars. Use whatever is available.
        avg_atr = market_data[atr_col].tail(8640).mean()

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
        # ATR * 100 converts gold ATR to $ per lot (approx)
        # For XAUUSD, 1 lot = 100 oz. 1 point = $0.01. ATR is in price.
        # So ATR * 100 is $ risk per lot.
        lot_size = (risk_amount / (current_atr * 100)) * total_multiplier if current_atr > 0 else 0.01

        # Cap at Max Position Size (10% of equity)
        max_notional = self.balance * self.cfg.max_position_size_pct
        price = market_data["close"].iloc[-1] if "close" in market_data.columns else 2300.0
        max_lots = max_notional / (price * 100) if price > 0 else 10.0

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
        Legacy fractional Kelly Criterion position sizing.
        DEPRECATED: Use calculate_position_size instead.
        """
        logger.warning("RiskManager.size_position() is deprecated. Use calculate_position_size() instead.")
        if avg_loss == 0:
            return 0.01
        kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        kelly_fraction = max(0.0, min(kelly_fraction, 0.25))
        risk_capital = self.balance * self.cfg.risk_per_trade
        lot_size = (risk_capital * kelly_fraction) / (avg_loss * pip_value)
        lot_size = max(0.01, round(lot_size, 2))
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

    # -- Internal cascade layers ----------------------------------------------

    def _check_circuit_breaker(self) -> bool:
        if self.peak_equity <= 0:
            return True
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

    def get_daily_loss_level(self) -> int:
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

    def get_size_multiplier_from_loss(self) -> float:
        level = self.get_daily_loss_level()
        mapping = {0: 1.0, 1: 1.0, 2: 0.5, 3: 0.25, 4: 0.0}
        return mapping.get(level, 0.0)

    def _check_directional_exposure(
        self, signal: TradeSignal, open_positions: List[Dict[str, Any]]
    ) -> bool:
        net_lots = 0.0
        for pos in open_positions:
            vol = pos.get("volume", 0.0)
            if pos.get("type") == 0:  # BUY
                net_lots += vol
            else:  # SELL
                net_lots -= vol

        net_lots += self.cfg.min_lot_size if signal.direction > 0 else -self.cfg.min_lot_size
        price_estimate = signal.entry_price
        notional = abs(net_lots) * price_estimate * 100
        exposure_pct = notional / self.balance if self.balance > 0 else 1.0
        return exposure_pct <= self.cfg.max_single_direction_pct

    def _check_total_notional(
        self, signal: TradeSignal, open_positions: List[Dict[str, Any]], market_data: pd.DataFrame
    ) -> bool:
        total_lots = sum(pos.get("volume", 0.0) for pos in open_positions) + self.cfg.min_lot_size
        price = market_data["close"].iloc[-1] if not market_data.empty else signal.entry_price
        total_notional = total_lots * price * 100
        return total_notional < (self.balance * self.cfg.max_total_notional_pct)

    def _check_symbol_allocation(self, symbol: str) -> bool:
        if symbol not in ALLOCATION_WEIGHTS and symbol != self.cfg.symbol:
            logger.warning("Symbol %s not in approved portfolio", symbol)
            return False
        return True

    def _check_risk_reward(self, signal: TradeSignal, min_rr: float = 1.5) -> bool:
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.entry_price)
        if risk == 0:
            return False
        rr = reward / risk
        return rr >= min_rr

    def _check_model_health(self, health: Optional[Dict[str, float]]) -> bool:
        if health is None:
            return True
        if float(health.get("drift", 0.0)) > self.cfg.model_drift_threshold:
            return False
        if float(health.get("accuracy", 1.0)) < self.cfg.model_accuracy_floor:
            return False
        if float(health.get("calibration", 0.0)) > self.cfg.model_calibration_threshold:
            return False
        return True


__all__ = ["ALLOCATION_WEIGHTS", "DailyStats", "RiskManager", "RiskDecision"]
