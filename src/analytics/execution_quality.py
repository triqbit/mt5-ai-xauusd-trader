"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/analytics/execution_quality.py
Execution efficiency and trade quality analytics.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

import numpy as np
from pydantic import BaseModel, Field
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.trade_logger import Base, ModelSignal, RiskEvent, Trade
from src.trading.mt5_connector import MT5Connector

logger = logging.getLogger(__name__)


class TradeExecutionQuality(BaseModel):
    """Execution metrics for a single executed trade."""

    trade_id: int
    ticket: int
    symbol: str
    slippage_pips: float = Field(
        ..., description="Difference between signal price and execution price"
    )
    execution_latency_ms: float = Field(..., description="Time between signal and execution in ms")
    fill_quality_score: float = Field(..., description="Normalized score 0-1 of fill quality")
    edge_capture: float = Field(..., description="Realized edge vs. theoretical edge")
    post_entry_drift_5m: float = Field(..., description="Price drift 5 mins after entry")
    post_entry_drift_15m: float = Field(..., description="Price drift 15 mins after entry")
    timing_efficiency: float = Field(
        ..., description="Score indicating if entry was at optimal time"
    )


class BlockedSignalQuality(BaseModel):
    """Opportunity cost analysis for rejected signals."""

    signal_id: int
    symbol: str
    rejection_reason: str
    opportunity_cost_pnl: float = Field(..., description="PnL missed by not executing this signal")
    max_favorable_excursion: float = Field(
        ..., description="Max favorable price movement after signal"
    )
    max_adverse_excursion: float = Field(..., description="Max adverse price movement after signal")
    would_have_won: bool = Field(..., description="True if signal would have hit TP before SL")


class ExecutionSummary(BaseModel):
    """Aggregate execution analytics."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    avg_slippage: float
    avg_latency_ms: float
    total_opportunity_cost: float
    avg_fill_quality: float
    execution_efficiency_score: float
    rejected_signal_count: int
    executed_trade_count: int


class ExecutionAnalyzer:
    """
    Institutional-grade execution quality analyzer.
    Correlates trades, signals, and market data to measure alpha decay and execution drag.
    """

    def __init__(
        self,
        db_url: str = "sqlite:///trades.db",
        connector: Optional[MT5Connector] = None,
    ) -> None:
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.connector = connector

    def analyze_trade(self, trade_id: int) -> Optional[TradeExecutionQuality]:
        """
        Analyze execution quality for a specific trade.
        Compares requested signal price vs actual execution price.
        """
        with self.Session() as session:
            trade = session.query(Trade).filter(Trade.id == trade_id).first()
            if not trade or not trade.signal:
                logger.warning("Trade %s or its signal not found for analysis", trade_id)
                return None

            signal = trade.signal
            symbol = trade.symbol

            # 1. Slippage calculation (in pips)
            # For XAUUSD, 1 pip = 0.1 price units
            pip_size = 0.1 if "XAUUSD" in symbol else 0.0001
            slippage_price = (trade.entry_price - signal.entry_price) * signal.direction
            slippage_pips = slippage_price / pip_size

            # 2. Latency calculation
            latency_td = trade.created_at - signal.timestamp
            latency_ms = max(0.0, latency_td.total_seconds() * 1000.0)

            # 3. Fill quality (0.0 to 1.0)
            # Simple decay model: 1.0 is perfect, loses 5% per pip slippage and 5% per second latency
            fill_quality = max(0.0, 1.0 - (abs(slippage_pips) * 0.05) - (latency_ms / 20000.0))

            # 4. Drift and Edge Capture (requires market data)
            drift_5m = self.calculate_drift(symbol, trade.created_at, signal.direction, 5)
            drift_15m = self.calculate_drift(symbol, trade.created_at, signal.direction, 15)
            edge_capture = self.calculate_edge_capture(trade, signal)

            # 5. Timing Efficiency
            timing_eff = self._calculate_timing_efficiency(trade)

            return TradeExecutionQuality(
                trade_id=trade.id,
                ticket=trade.ticket,
                symbol=symbol,
                slippage_pips=float(slippage_pips),
                execution_latency_ms=float(latency_ms),
                fill_quality_score=float(fill_quality),
                edge_capture=float(edge_capture),
                post_entry_drift_5m=float(drift_5m),
                post_entry_drift_15m=float(drift_15m),
                timing_efficiency=float(timing_eff),
            )

    def calculate_drift(
        self, symbol: str, start_time: datetime, direction: int, minutes: int
    ) -> float:
        """Calculate price movement N minutes after entry."""
        if not self.connector:
            return 0.0

        # Fetch 1-minute bars to get granular drift
        # Note: start_time is UTC, MT5 might need conversion depending on broker
        # We assume MT5Connector handles timeframes correctly.
        df = self.connector.get_rates(symbol, "M1", minutes + 1)
        if df.empty or len(df) < minutes:
            return 0.0

        # Calculate drift from entry candle to N candles later
        # This is a simplified version; real drift should use trade entry time exactly
        entry_price = df.iloc[0]["close"]
        later_price = df.iloc[-1]["close"]

        drift = (later_price - entry_price) * direction
        pip_size = 0.1 if "XAUUSD" in symbol else 0.0001
        return float(drift / pip_size)

    def calculate_edge_capture(self, trade: Trade, signal: ModelSignal) -> float:
        """
        Measure realized edge vs theoretical edge.
        Edge = (Exit - Entry) / Volatility
        """
        if not trade.exit_price or not signal.volatility or signal.volatility == 0:
            return 0.0

        theoretical_edge = (signal.take_profit - signal.entry_price) * signal.direction
        realized_edge = (trade.exit_price - trade.entry_price) * signal.direction

        if theoretical_edge == 0:
            return 0.0

        return float(realized_edge / theoretical_edge)

    def _calculate_timing_efficiency(self, trade: Trade) -> float:
        """
        Determine if entry was at a local extreme of the entry candle.
        Score 1.0 means we entered at the best possible price of that minute.
        """
        if not self.connector:
            return 0.5

        df = self.connector.get_rates(trade.symbol, "M1", 1)
        if df.empty:
            return 0.5

        row = df.iloc[0]
        high, low = row["high"], row["low"]
        range_val = high - low

        if range_val == 0:
            return 1.0

        if trade.direction > 0:  # Buy
            # Better price is lower
            efficiency = (high - trade.entry_price) / range_val
        else:  # Sell
            # Better price is higher
            efficiency = (trade.entry_price - low) / range_val

        return float(np.clip(efficiency, 0.0, 1.0))

    def analyze_blocked_signals(self, start_time: datetime) -> List[BlockedSignalQuality]:
        """
        Evaluate opportunity cost of signals rejected by risk management.
        Calculates what would have happened if the trade was taken.
        """
        results = []
        with self.Session() as session:
            # Find signals that have a RiskEvent and NO Trade
            blocked_events = (
                session.query(RiskEvent)
                .filter(
                    RiskEvent.created_at >= start_time,
                    RiskEvent.event_type == "SIGNAL_REJECTED",
                    RiskEvent.signal_id.isnot(None),
                )
                .all()
            )

            for event in blocked_events:
                signal = (
                    session.query(ModelSignal).filter(ModelSignal.id == event.signal_id).first()
                )
                if not signal or signal.trade:
                    continue

                analysis = self._evaluate_opportunity_cost(signal, event.description)
                if analysis:
                    results.append(analysis)

        return results

    def _evaluate_opportunity_cost(
        self, signal: ModelSignal, reason: str
    ) -> Optional[BlockedSignalQuality]:
        """
        Calculate MFE, MAE, and potential PnL for a rejected signal.
        """
        if not self.connector:
            return None

        # Fetch up to 100 bars after signal to see outcome
        df = self.connector.get_rates(signal.symbol, "M15", 100)
        if df.empty:
            return None

        # Filter bars that happened AFTER the signal
        # Use a small buffer to account for clock drift
        df = df[df["time"] >= signal.timestamp]
        if df.empty:
            return None

        # Calculate excursions
        prices = df["close"].values
        highs = df["high"].values
        lows = df["low"].values

        if signal.direction > 0:  # BUY
            prices - signal.entry_price
            mfe = np.max(highs) - signal.entry_price
            mae = signal.entry_price - np.min(lows)

            # Check if TP or SL would hit first
            would_win = False
            for price_high, price_low in zip(highs, lows, strict=False):
                if price_high >= (signal.take_profit or float("inf")):
                    would_win = True
                    break
                if price_low <= (signal.stop_loss or float("-inf")):
                    would_win = False
                    break

            opp_cost = (prices[-1] - signal.entry_price) * signal.lot_size * 100  # XAUUSD
        else:  # SELL
            signal.entry_price - prices
            mfe = signal.entry_price - np.min(lows)
            mae = np.max(highs) - signal.entry_price

            # Check if TP or SL would hit first
            would_win = False
            for price_high, price_low in zip(highs, lows, strict=False):
                if price_low <= (signal.take_profit or float("-inf")):
                    would_win = True
                    break
                if price_high >= (signal.stop_loss or float("inf")):
                    would_win = False
                    break

            opp_cost = (signal.entry_price - prices[-1]) * signal.lot_size * 100

        return BlockedSignalQuality(
            signal_id=signal.id,
            symbol=signal.symbol,
            rejection_reason=reason,
            opportunity_cost_pnl=float(opp_cost),
            max_favorable_excursion=float(mfe),
            max_adverse_excursion=float(mae),
            would_have_won=would_win,
        )

    def generate_summary_report(self, days: int = 7) -> ExecutionSummary:
        """Aggregate execution quality metrics into a summary report."""
        from datetime import timedelta

        start_time = datetime.now(timezone.utc) - timedelta(days=days)

        with self.Session() as session:
            trades = session.query(Trade).filter(Trade.created_at >= start_time).all()

            qualities = []
            for t in trades:
                q = self.analyze_trade(t.id)
                if q:
                    qualities.append(q)

            blocked = self.analyze_blocked_signals(start_time)

            if not qualities:
                return ExecutionSummary(
                    avg_slippage=0.0,
                    avg_latency_ms=0.0,
                    total_opportunity_cost=sum(b.opportunity_cost_pnl for b in blocked),
                    avg_fill_quality=0.0,
                    execution_efficiency_score=0.0,
                    rejected_signal_count=len(blocked),
                    executed_trade_count=0,
                )

            avg_slippage = np.mean([q.slippage_pips for q in qualities])
            avg_latency = np.mean([q.execution_latency_ms for q in qualities])
            avg_fill = np.mean([q.fill_quality_score for q in qualities])

            # Execution efficiency score is a weighted blend
            eff_score = (avg_fill * 0.7) + (max(0.0, 1.0 - (avg_latency / 5000.0)) * 0.3)

            return ExecutionSummary(
                avg_slippage=float(avg_slippage),
                avg_latency_ms=float(avg_latency),
                total_opportunity_cost=float(sum(b.opportunity_cost_pnl for b in blocked)),
                avg_fill_quality=float(avg_fill),
                execution_efficiency_score=float(eff_score),
                rejected_signal_count=len(blocked),
                executed_trade_count=len(qualities),
            )
