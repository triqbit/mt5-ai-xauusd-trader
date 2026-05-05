"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/risk_engine.py
Enterprise risk management engine implementing:
  - ATR-based position sizing (14-period vs 30-day average)
  - Cascading daily loss circuit breakers (Level 1-4)
  - Drawdown safeguards and exposure limits
  - Signal validation against hard risk limits
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

import pandas as pd

from src.core.config import TradingConfig
from src.core.monitor import Monitor
from src.core.trade_logger import TradeLogger

logger = logging.getLogger(__name__)


@dataclass
class RiskDecision:
    """Decision details from the RiskEngine."""

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


class RiskEngine:
    """
    Institutional risk engine.
    Enforces RISK_LIMITS.md safeguards.
    """

    def __init__(
        self,
        config: TradingConfig,
        account_balance: float,
        trade_logger: Optional[TradeLogger] = None,
        monitor: Optional[Monitor] = None,
    ) -> None:
        self.cfg = config
        self.balance = account_balance
        self.peak_equity = account_balance
        self.daily = DailyStats(peak_equity=account_balance)
        self.trade_logger = trade_logger
        self.monitor = monitor
        logger.info("RiskEngine initialised | balance=%.2f", account_balance)

    def validate_signal(
        self, signal: Any, market_data: pd.DataFrame, open_positions: list[dict[str, Any]]
    ) -> RiskDecision:
        """
        Validate a trade signal against all risk layers from RISK_LIMITS.md.

        Layers:
          1. Circuit Breakers (Drawdown, Daily Loss Level 4).
          2. Activity Limits (Max Daily Trades, Losing Streaks).
          3. Exposure Limits (Max Positions, Net Directional Exposure, Total Notional).
          4. Prediction Limits (Confidence threshold).
          5. Sizing & Liquidity (ATR sizing, Min lots).

        Args:
            signal: TradeSignal-like object to validate.
            market_data: Historical OHLCV + Indicators.
            open_positions: List of active position dictionaries.

        Returns:
            RiskDecision: Approval status and reason.
        """
        # 1. Circuit Breakers
        if not self._check_drawdown_breaker():
            return RiskDecision(False, "Hard drawdown limit reached")

        if self.get_daily_loss_level() >= 4:
            return RiskDecision(False, "Daily loss limit reached (Level 4)")

        # 2. Activity Limits
        if self.daily.trade_count >= self.cfg.max_trades_per_day:
            return RiskDecision(False, "Max daily trades reached")

        if self.daily.consecutive_losses >= self.cfg.max_losing_streak:
            return RiskDecision(False, "Max consecutive losses reached")

        # 3. Exposure Limits
        if len(open_positions) >= self.cfg.max_positions:
            return RiskDecision(False, "Max concurrent positions reached")

        # Total Notional (< 100% of equity)
        if not self._check_total_notional(signal, open_positions, market_data):
            return RiskDecision(False, "Total notional exposure exceeds equity")

        # Net Directional Exposure (Max 30% per direction)
        if not self._check_directional_exposure(signal, open_positions, market_data):
            return RiskDecision(False, "Max directional exposure reached (30%)")

        # 4. Prediction Limits
        if signal.confidence < self.cfg.min_confidence:
            return RiskDecision(
                False, f"Confidence {signal.confidence:.2f} below {self.cfg.min_confidence}"
            )

        # 5. Sizing & Liquidity
        # ATR-based position sizing adjustment
        adjusted_lots = self.calculate_position_size(signal.symbol, market_data)

        if adjusted_lots < self.cfg.min_lot_size:
            return RiskDecision(False, f"Calculated lot size {adjusted_lots} below minimum")

        return RiskDecision(True, "Approved", adjusted_lots)

    def _check_directional_exposure(
        self, signal: Any, open_positions: list[dict[str, Any]], market_data: pd.DataFrame
    ) -> bool:
        """
        Enforce max 30% net long OR short exposure.
        For simplicity in this core module, we treat all positions as correlated (XAUUSD focus).
        """
        net_lots = 0.0
        # MT5 positions have 'type' (0=buy, 1=sell) and 'volume'
        for pos in open_positions:
            vol = pos.get("volume", 0.0)
            if pos.get("type") == 0:  # BUY
                net_lots += vol
            else:  # SELL
                net_lots -= vol

        # Add proposed signal
        if signal.direction > 0:
            net_lots += self.cfg.min_lot_size  # estimate with min lots for exposure check
        else:
            net_lots -= self.cfg.min_lot_size

        # Convert lots to approx notional exposure %
        # (Net Lots * Price * 100) / Balance
        # For gold at 2300: 0.1 lots = 10oz = $23,000. Balance 100k -> 23%
        # We cap net notional at 30%
        price_estimate = 2300.0
        if not market_data.empty:
            price_estimate = market_data["close"].iloc[-1]

        notional = abs(net_lots) * price_estimate * 100
        exposure_pct = notional / self.balance if self.balance > 0 else 1.0

        return exposure_pct <= self.cfg.max_single_direction_pct

    def _check_total_notional(
        self, signal: Any, open_positions: list[dict[str, Any]], market_data: pd.DataFrame
    ) -> bool:
        """Enforce total notional exposure < 100% of account equity."""
        total_lots = sum(pos.get("volume", 0.0) for pos in open_positions)
        total_lots += self.cfg.min_lot_size  # plus proposed

        price = market_data["close"].iloc[-1] if not market_data.empty else 2300.0
        total_notional = total_lots * price * 100
        return total_notional < (self.balance * self.cfg.max_total_notional_pct)

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
          - Daily loss level multiplier.
          - Max Risk per trade (1% of balance).
          - Max Position Size (10% of account equity).
          - Min Position Size (0.01 lot).

        Args:
            symbol: Trading symbol (e.g., XAUUSD).
            market_data: DataFrame containing 'atr' and 'close' columns.

        Returns:
            float: Calculated lot size.
        """
        if market_data.empty or "atr" not in market_data.columns:
            logger.warning("No ATR data available for sizing, using default minimum risk.")
            return self.cfg.min_lot_size

        current_atr = market_data["atr"].iloc[-1]
        # Approx 30 days of M5 data (12 bars/hr * 24 hr/day * 30 days = 8640 bars)
        # Use whatever history is available if < 8640
        avg_atr = market_data["atr"].tail(8640).mean()

        vol_multiplier = 1.0
        ratio = current_atr / avg_atr if avg_atr > 0 else 1.0

        if ratio > self.cfg.volatility_extreme_threshold:
            logger.warning("Extreme volatility (%.2fx) - HALTING", ratio)
            return 0.0
        if ratio > self.cfg.volatility_very_high_threshold:
            vol_multiplier = 0.5
        elif ratio > self.cfg.volatility_high_threshold:
            vol_multiplier = 0.75

        # Factor in daily loss level reduction
        loss_multiplier = self.get_size_multiplier_from_loss()
        total_multiplier = vol_multiplier * loss_multiplier

        if total_multiplier <= 0:
            return 0.0

        # Basic risk-based sizing: risk X% of balance
        # For XAUUSD, 1 lot = 100 oz. $1 price change = $100 per lot.
        # lot_size = (balance * risk_per_trade) / (ATR * 100)
        risk_amount = self.balance * self.cfg.risk_per_trade
        lot_size = (risk_amount / (current_atr * 100)) * total_multiplier

        # Cap at Max Position Size (e.g., 10% of equity)
        max_notional = self.balance * self.cfg.max_position_size_pct
        price = market_data["close"].iloc[-1]
        # Notional = Price * Volume * ContractSize(100 for gold)
        max_lots = max_notional / (price * 100)

        final_lots = min(lot_size, max_lots)
        final_lots = max(self.cfg.min_lot_size, round(final_lots, 2))

        logger.debug(
            "Sizing %s | ratio=%.2f vol_mult=%.2f loss_mult=%.2f final_lots=%.2f",
            symbol,
            ratio,
            vol_multiplier,
            loss_multiplier,
            final_lots,
        )

        return final_lots

    def update_metrics(self, current_equity: float, realized_pnl: float = 0) -> None:
        """Update internal trackers."""
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

    # -- Internal Breakers --------------------------------------------------
    def _check_drawdown_breaker(self) -> bool:
        drawdown = (self.peak_equity - self.balance) / self.peak_equity
        return drawdown < self.cfg.max_drawdown

    def _check_daily_loss_breaker(self) -> bool:
        if self.daily.peak_equity <= 0:
            return True
        loss_pct = abs(self.daily.realised_pnl) / self.daily.peak_equity
        return not (self.daily.realised_pnl < 0 and loss_pct >= self.cfg.max_daily_loss)

    def get_daily_loss_level(self) -> int:
        """
        Returns cascading loss level 0-4 based on RISK_LIMITS.md.

        Levels:
          0: Normal
          1: Yellow Alert (2% loss) -> Alert
          2: Orange Alert (3% loss) -> Reduce position size to 50%
          3: Red Alert (4% loss) -> Reduce position size to 25%
          4: Emergency Stop (5% loss) -> HALT ALL TRADING

        Returns:
            int: Loss level from 0 to 4.
        """
        if self.daily.peak_equity <= 0:
            return 0

        # Only count losses
        if self.daily.realised_pnl >= 0:
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
        """
        Calculates position size multiplier based on current daily loss level.

        Returns:
            float: Multiplier (1.0, 0.5, 0.25, or 0.0).
        """
        level = self.get_daily_loss_level()
        if level >= 4:
            return 0.0
        if level == 3:
            return 0.25
        if level == 2:
            return 0.5
        return 1.0


__all__ = ["DailyStats", "RiskDecision", "RiskEngine"]
