"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/analytics/execution_quality.py
Measures execution efficiency and trade quality to distinguish alpha from execution.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
from pydantic import BaseModel, Field


class ExecutionMetrics(BaseModel):
    """Detailed execution performance metrics for a single trade."""

    ticket: int
    symbol: str
    slippage_pips: float = Field(..., description="Execution slippage in pips.")
    fill_quality_score: float = Field(..., ge=0.0, le=1.0, description="Score from 0 to 1.")
    timing_efficiency: float = Field(..., ge=0.0, le=1.0, description="How well timed the entry was.")
    edge_capture: float = Field(..., description="Spread-adjusted edge capture.")
    post_entry_drift_pips: Dict[str, float] = Field(default_factory=dict, description="Price drift after entry.")


class FillQuality(BaseModel):
    """Summary of fill quality across multiple trades."""

    average_slippage: float
    average_fill_score: float
    total_trades_analyzed: int
    slippage_by_algorithm: Dict[str, float]


class TradeQualityReport(BaseModel):
    """Aggregate report of execution and alpha quality."""

    execution_metrics: List[ExecutionMetrics]
    aggregate_fill_quality: FillQuality
    blocked_trade_opportunity_cost: float = Field(..., description="Total PnL missed by rejected signals.")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ExecutionAnalyzer:
    """
    Institutional-grade execution analysis engine.
    Distinguishes alpha quality (strategy intent) from execution quality (fill efficiency).
    """

    def __init__(self, symbol: str = "XAUUSD"):
        self.symbol = symbol
        # XAUUSD pip multiplier: usually 1.00 move = 100 pips (0.01 = 1 pip)
        self.pip_multiplier = 100.0 if "XAUUSD" in symbol else 10000.0

    def calculate_slippage(
        self, requested_price: float, execution_price: float, direction: int
    ) -> float:
        """
        Calculates slippage in pips.
        Positive slippage means a worse price than requested.
        """
        # direction: +1 for Buy, -1 for Sell
        raw_slippage = (execution_price - requested_price) * direction
        return raw_slippage * self.pip_multiplier

    def calculate_fill_quality(self, slippage_pips: float, spread_pips: float) -> float:
        """
        Calculates a fill quality score from 0.0 to 1.0.
        Score = 1.0 - (Slippage / (2 * Spread)) capped at 0 and 1.
        """
        if spread_pips <= 0:
            return 1.0 if slippage_pips <= 0 else 0.0

        # If slippage is half the spread or less, it's a good fill.
        # If slippage exceeds spread, quality drops quickly.
        score = 1.0 - (max(0, slippage_pips) / (spread_pips * 2))
        return float(np.clip(score, 0.0, 1.0))

    def analyze_timing_efficiency(
        self, entry_price: float, window_high: float, window_low: float, direction: int
    ) -> float:
        """
        Measures where the entry price sits within a price window (e.g., entry candle).
        For a Buy (+1): (High - Entry) / (High - Low). 1.0 means bought at the exact bottom.
        For a Sell (-1): (Entry - Low) / (High - Low). 1.0 means sold at the exact top.
        """
        range_size = window_high - window_low
        if range_size <= 0:
            return 1.0

        if direction == 1:  # Buy
            efficiency = (window_high - entry_price) / range_size
        else:  # Sell
            efficiency = (entry_price - window_low) / range_size

        return float(np.clip(efficiency, 0.0, 1.0))

    def measure_edge_capture(
        self,
        entry_price: float,
        exit_price: float,
        avg_spread_pips: float,
        direction: int,
    ) -> float:
        """
        Calculates spread-adjusted edge capture.
        (Gross Profit in Pips - Average Spread) / Average Spread
        """
        pips_gained = (exit_price - entry_price) * direction * self.pip_multiplier
        if avg_spread_pips <= 0:
            return pips_gained

        edge = (pips_gained - avg_spread_pips) / avg_spread_pips
        return float(edge)

    def analyze_post_entry_drift(
        self, entry_price: float, price_at_intervals: Dict[str, float], direction: int
    ) -> Dict[str, float]:
        """
        Analyzes price movement at various intervals after entry.
        Intervals could be '5m', '15m', '1h', etc.
        """
        drift = {}
        for label, price in price_at_intervals.items():
            move = (price - entry_price) * direction * self.pip_multiplier
            drift[label] = float(move)
        return drift

    def evaluate_blocked_trade(
        self, signal_price: float, hypothetical_exit: float, direction: int
    ) -> float:
        """
        Calculates the opportunity cost (or saved loss) from a blocked/rejected signal.
        Returns hypothetical PnL in pips.
        """
        return (hypothetical_exit - signal_price) * direction * self.pip_multiplier
