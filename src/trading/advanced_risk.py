"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/advanced_risk.py
Advanced risk management rules and protection mechanisms.
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from src.core.config import TradingConfig

logger = logging.getLogger(__name__)

class VolatilityRegime(Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    EXTREME = "EXTREME"

class AdvancedRiskManager:
    """
    Implements advanced protection mechanisms for capital preservation.
    """

    def __init__(self, config: TradingConfig) -> None:
        self.cfg = config

    def check_correlation(
        self,
        symbol: str,
        open_positions: List[str],
        historical_data: Dict[str, pd.Series]
    ) -> bool:
        """
        Check if the new symbol has a high correlation with existing open positions.
        Returns False if correlation exceeds the threshold.
        """
        if not open_positions or symbol not in historical_data:
            return True

        new_series = historical_data[symbol]

        for pos_symbol in open_positions:
            if pos_symbol in historical_data:
                # Calculate Pearson correlation of returns
                corr = new_series.corr(historical_data[pos_symbol])
                if abs(corr) > self.cfg.max_correlation:
                    logger.warning(
                        "Correlation too high: %s vs %s (%.2f > %.2f)",
                        symbol, pos_symbol, corr, self.cfg.max_correlation
                    )
                    return False
        return True

    def check_time_exposure(self, recent_trades: List[Dict[str, Any]], current_time: datetime) -> bool:
        """
        Check if the total risk taken in the last hour exceeds the limit.
        recent_trades should contain 'timestamp' and 'risk_amount' (as fraction of equity).
        """
        hour_ago = current_time - timedelta(hours=1)
        hourly_risk = sum(
            t["risk_amount"] for t in recent_trades
            if t["timestamp"] >= hour_ago
        )

        if hourly_risk > self.cfg.max_risk_per_hour:
            logger.warning("Hourly risk limit hit: %.4f > %.4f", hourly_risk, self.cfg.max_risk_per_hour)
            return False
        return True

    def detect_volatility_regime(self, df: pd.DataFrame) -> VolatilityRegime:
        """
        Detect the current volatility regime based on ATR.
        Requires 'high', 'low', 'close' columns in df.
        """
        if len(df) < 30:
            return VolatilityRegime.NORMAL

        # Calculate ATR
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(14).mean()

        current_atr = atr.iloc[-1]
        avg_atr = atr.rolling(30).mean().iloc[-1]

        if np.isnan(current_atr) or np.isnan(avg_atr):
            return VolatilityRegime.NORMAL

        ratio = current_atr / avg_atr

        if ratio > 2.5:
            return VolatilityRegime.EXTREME
        elif ratio > 1.5:
            return VolatilityRegime.HIGH
        elif ratio < 0.5:
            return VolatilityRegime.LOW
        else:
            return VolatilityRegime.NORMAL

    def calculate_portfolio_heat(self, open_positions: List[Dict[str, Any]], equity: float) -> float:
        """
        Calculate the current portfolio heat (total % of equity at risk).
        Each position should have 'sl_distance' (pips/price) and 'lot_size'.
        """
        if equity <= 0:
            return 0.0

        total_risk = 0.0
        for pos in open_positions:
            # risk = sl_distance * lot_size * pip_value_multiplier
            # Simplification: risk is provided in the position dict
            total_risk += pos.get("risk_amount", 0.0)

        return total_risk / equity

    def check_consecutive_losses(self, trade_history: List[Dict[str, Any]]) -> bool:
        """
        Check if the maximum number of consecutive losses has been reached.
        trade_history should be sorted from newest to oldest.
        """
        if not trade_history:
            return True

        loss_count = 0
        for trade in trade_history:
            if trade.get("pnl", 0) < 0:
                loss_count += 1
                if loss_count >= self.cfg.max_consecutive_losses:
                    logger.warning("Max consecutive losses reached: %d", loss_count)
                    return False
            else:
                break
        return True

    def is_news_halted(self, current_time: datetime, news_events: List[Dict[str, Any]]) -> bool:
        """
        Check if trading should be halted due to high-impact news.
        news_events: list of dicts with 'timestamp' and 'impact' (e.g. 'HIGH').
        """
        window = timedelta(minutes=self.cfg.news_halt_window)

        for event in news_events:
            if event.get("impact") == "HIGH":
                event_time = event["timestamp"]
                if (event_time - window) <= current_time <= (event_time + window):
                    logger.warning("Trading halted due to high-impact news at %s", event_time)
                    return True
        return False

    def verify_slippage(
        self,
        expected_price: float,
        actual_price: float,
        direction: int,
        pip_value: float = 0.1
    ) -> bool:
        """
        Verify if the slippage is within acceptable limits.
        direction: 1 for BUY, -1 for SELL
        """
        if expected_price <= 0:
            return True

        if direction == 1: # BUY: actual price > expected price is negative slippage
            slippage = (actual_price - expected_price) / pip_value
        else: # SELL: actual price < expected price is negative slippage
            slippage = (expected_price - actual_price) / pip_value

        if slippage > self.cfg.max_slippage_pips:
            logger.warning("Slippage too high: %.2f pips > %.2f", slippage, self.cfg.max_slippage_pips)
            return False
        return True
