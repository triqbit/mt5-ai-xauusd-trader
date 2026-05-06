"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/analytics/execution_quality.py
Execution efficiency and trade quality analytics.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

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
    spread_at_execution: float = Field(..., description="Spread in pips at time of execution")
    slippage_to_spread_ratio: float = Field(
        ..., description="Slippage relative to spread (lower is better)"
    )
    alpha_decay_pips: float = Field(
        ..., description="Alpha lost between signal and execution (pips)"
    )
    execution_cost_pips: float = Field(
        ..., description="Total cost of execution (slippage + half spread)"
    )
    markout_pnls: dict[str, float] = Field(
        default_factory=dict, description="Price drift at various horizons (1m, 5m, 15m, 30m, 60m)"
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

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    avg_slippage: float
    avg_latency_ms: float
    total_opportunity_cost: float
    avg_fill_quality: float
    avg_edge_capture: float
    avg_timing_efficiency: float
    avg_alpha_decay: float
    execution_efficiency_score: float
    rejected_signal_count: int
    executed_trade_count: int

    def to_report_section(self) -> Any:
        """Convert to reporting model."""
        from src.research.reporting import ExecutionMetric, ExecutionQualitySection

        metrics = [
            ExecutionMetric(
                name="Avg Slippage",
                value=f"{self.avg_slippage:.2f} pips",
                status="OK" if abs(self.avg_slippage) < 1.0 else "WARNING",
            ),
            ExecutionMetric(
                name="Avg Latency",
                value=f"{self.avg_latency_ms:.0f}ms",
                status="OK" if self.avg_latency_ms < 500 else "WARNING",
            ),
            ExecutionMetric(
                name="Fill Quality",
                value=f"{self.avg_fill_quality:.2%}",
                status="OK" if self.avg_fill_quality > 0.8 else "WARNING",
            ),
            ExecutionMetric(
                name="Edge Capture",
                value=f"{self.avg_edge_capture:.2%}",
                status="OK" if self.avg_edge_capture > 0.5 else "WARNING",
            ),
            ExecutionMetric(
                name="Timing Efficiency",
                value=f"{self.avg_timing_efficiency:.2%}",
                status="OK",
            ),
            ExecutionMetric(
                name="Alpha Decay",
                value=f"{self.avg_alpha_decay:.2f} pips",
                status="OK",
            ),
        ]

        return ExecutionQualitySection(
            efficiency_score=float(self.execution_efficiency_score * 100),
            metrics=metrics,
            opportunity_cost=f"${self.total_opportunity_cost:,.2f}",
            trade_count=self.executed_trade_count,
            rejected_count=self.rejected_signal_count,
        )


class ExecutionAnalyzer:
    """
    Institutional-grade execution quality analyzer.
    Correlates trades, signals, and market data to measure alpha decay and execution drag.
    """

    def __init__(
        self,
        db_url: str = "sqlite:///trades.db",
        connector: MT5Connector | None = None,
    ) -> None:
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.connector = connector

    def _get_pip_size(self, symbol: str) -> float:
        """Utility to get pip size for a symbol."""
        if self.connector:
            props = self.connector.get_symbol_properties(symbol)
            if props and "digits" in props:
                digits = props["digits"]
                # For XAUUSD, digits is usually 2 or 3. Pip is 0.1 (digits-1)
                # For EURUSD, digits is 5. Pip is 0.0001 (digits-1)
                # Heuristic: 10 ^ -(digits - 1)
                return 10 ** -(digits - 1)

        if any(x in symbol for x in ["XAUUSD", "GOLD"]):
            return 0.1
        if any(x in symbol for x in ["JPY", "HUF"]):
            return 0.01
        return 0.0001

    def _get_contract_size(self, symbol: str) -> float:
        """Utility to get contract size for a symbol."""
        if self.connector:
            props = self.connector.get_symbol_properties(symbol)
            if props and "contract_size" in props:
                return float(props["contract_size"])

        if any(x in symbol for x in ["XAUUSD", "GOLD"]):
            return 100.0
        return 100000.0

    def analyze_trade(self, trade_id: int) -> TradeExecutionQuality | None:
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
            pip_size = self._get_pip_size(symbol)
            slippage_price = (trade.entry_price - signal.entry_price) * signal.direction
            slippage_pips = slippage_price / pip_size

            # 2. Latency calculation
            t_created = trade.created_at.replace(tzinfo=UTC) if trade.created_at.tzinfo is None else trade.created_at
            s_timestamp = signal.timestamp.replace(tzinfo=UTC) if signal.timestamp.tzinfo is None else signal.timestamp
            latency_td = t_created - s_timestamp
            latency_ms = max(0.0, latency_td.total_seconds() * 1000.0)

            # 3. Spread calculation
            spread_info = self._get_execution_spread(trade)
            spread_pips = spread_info["spread_pips"]

            # 4. Fill quality (0.0 to 1.0)
            # Spread-relative decay model: better handles different market conditions
            slippage_ratio = (
                abs(slippage_pips) / spread_pips if spread_pips > 0.1 else abs(slippage_pips)
            )
            # Sigmoid-like penalty: small slippage is okay, large slippage is penalized heavily
            fill_quality = 1.0 / (1.0 + np.exp(slippage_ratio - 2.0))
            # Also penalize latency (10s latency halves quality)
            fill_quality *= max(0.0, 1.0 - (latency_ms / 10000.0))

            # 5. Drift and Edge Capture (requires market data)
            markout_horizons = [1, 5, 15, 30, 60]
            markouts = self.calculate_markouts(
                symbol, trade.created_at, trade.entry_price, trade.direction, markout_horizons
            )
            edge_capture = self.calculate_edge_capture(trade, signal)

            # 6. Timing Efficiency
            timing_eff = self._calculate_timing_efficiency(trade)

            # 7. Alpha Decay and Total Cost
            alpha_decay = self.calculate_alpha_decay(trade, signal)
            execution_cost = abs(slippage_pips) + (spread_pips / 2.0)

            return TradeExecutionQuality(
                trade_id=trade.id,
                ticket=trade.ticket,
                symbol=symbol,
                slippage_pips=float(slippage_pips),
                execution_latency_ms=float(latency_ms),
                fill_quality_score=float(fill_quality),
                edge_capture=float(edge_capture),
                post_entry_drift_5m=float(markouts.get("5m", 0.0)),
                post_entry_drift_15m=float(markouts.get("15m", 0.0)),
                timing_efficiency=float(timing_eff),
                spread_at_execution=float(spread_pips),
                slippage_to_spread_ratio=float(slippage_ratio),
                alpha_decay_pips=float(alpha_decay),
                execution_cost_pips=float(execution_cost),
                markout_pnls=markouts,
            )

    def calculate_drift(
        self, symbol: str, start_time: datetime, direction: int, minutes: int
    ) -> float:
        """Calculate price movement N minutes after entry."""
        if not self.connector:
            return 0.0

        pip_size = self._get_pip_size(symbol)
        end_time = start_time + timedelta(minutes=minutes + 1)

        df = self.connector.get_rates_range(symbol, "M1", start_time, end_time)
        if df.empty:
            return 0.0

        entry_price = df.iloc[0]["close"]
        later_price = df.iloc[-1]["close"]

        drift = (later_price - entry_price) * direction
        return float(drift / pip_size)

    def calculate_markouts(
        self,
        symbol: str,
        entry_time: datetime,
        entry_price: float,
        direction: int,
        horizons: list[int],
    ) -> dict[str, float]:
        """
        Calculate price drift at various horizons (in minutes) after entry.
        Markouts help distinguish alpha quality from execution quality.
        """
        if not self.connector or not horizons:
            return {}

        if entry_time.tzinfo is None:
            entry_time = entry_time.replace(tzinfo=UTC)

        pip_size = self._get_pip_size(symbol)
        max_horizon = max(horizons)
        # Fetch data once for all horizons
        end_time = entry_time + timedelta(minutes=max_horizon + 2)
        df = self.connector.get_rates_range(symbol, "M1", entry_time, end_time)

        if df.empty:
            return {f"{h}m": 0.0 for h in horizons}

        # Ensure df['time'] is UTC aware
        if df["time"].dt.tz is None:
            df["time"] = df["time"].dt.tz_localize(UTC)

        results = {}
        for h in horizons:
            target_time = entry_time + timedelta(minutes=h)

            # Find the row closest to target_time
            # Since we use M1, we can find it by index or by time comparison
            mask = df["time"] >= target_time
            if mask.any():
                later_price = df[mask].iloc[0]["close"]
            else:
                later_price = df.iloc[-1]["close"]

            drift = (later_price - entry_price) * direction
            results[f"{h}m"] = float(drift / pip_size)

        return results

    def calculate_alpha_decay(self, trade: Trade, signal: ModelSignal) -> float:
        """
        Measure how much price moved against the signal direction between
        signal timestamp and trade creation time.
        """
        if not self.connector:
            return 0.0

        pip_size = self._get_pip_size(trade.symbol)

        t_created = trade.created_at.replace(tzinfo=UTC) if trade.created_at.tzinfo is None else trade.created_at
        s_timestamp = signal.timestamp.replace(tzinfo=UTC) if signal.timestamp.tzinfo is None else signal.timestamp

        # Movement between signal price and execution price that is NOT slippage
        # In this context, let's define it as the price movement in the market
        # during the latency period.
        df = self.connector.get_rates_range(trade.symbol, "M1", s_timestamp, t_created)
        if df.empty or len(df) < 2:
            return 0.0

        market_move = (df.iloc[-1]["close"] - df.iloc[0]["open"]) * signal.direction
        return float(market_move / pip_size)

    def calculate_edge_capture(self, trade: Trade, signal: ModelSignal) -> float:
        """
        Measure realized edge vs theoretical edge, adjusted for spread.
        Edge Capture = (Realized PnL - Half Spread) / Theoretical PnL
        """
        if not trade.exit_price or not signal.take_profit:
            return 0.0

        pip_size = self._get_pip_size(trade.symbol)
        spread_info = self._get_execution_spread(trade)
        half_spread_pips = spread_info["spread_pips"] / 2.0

        # Theoretical move from signal price to signal TP
        theoretical_move = abs(signal.take_profit - signal.entry_price)

        # Realized move from execution price to exit price
        realized_move = (trade.exit_price - trade.entry_price) * trade.direction

        if theoretical_move == 0:
            return 0.0

        # Adjust realized move by subtracting the "cost" of the half-spread we'd ideally not pay
        # This highlights how much of the available alpha we got AFTER friction
        adjusted_realized = (realized_move / pip_size) - half_spread_pips
        theoretical_pips = theoretical_move / pip_size

        return float(np.clip(adjusted_realized / theoretical_pips, 0.0, 1.2))

    def _get_execution_spread(self, trade: Trade) -> dict[str, float]:
        """Estimate spread at the time of execution."""
        if not self.connector:
            return {"spread_pips": 0.0}

        pip_size = self._get_pip_size(trade.symbol)
        t_created = trade.created_at.replace(tzinfo=UTC) if trade.created_at.tzinfo is None else trade.created_at

        # Fetch data around execution time
        df = self.connector.get_rates_range(
            trade.symbol, "M1", t_created - timedelta(minutes=1), t_created
        )

        if df.empty:
            return {"spread_pips": 2.0}  # Default for XAUUSD

        # MT5 'spread' in rates is in points
        point_size = 0.01 if "XAUUSD" in trade.symbol else 0.00001
        avg_spread_points = df["spread"].mean()
        spread_pips = (avg_spread_points * point_size) / pip_size

        return {"spread_pips": float(spread_pips)}

    def _calculate_timing_efficiency(self, trade: Trade) -> float:
        """
        Determine if entry was at a local extreme of the entry candle.
        Score 1.0 means we entered at the best possible price of that minute.
        """
        if not self.connector:
            return 0.5

        t_created = trade.created_at.replace(tzinfo=UTC) if trade.created_at.tzinfo is None else trade.created_at

        # Fetch exactly the candle where the trade was created
        df = self.connector.get_rates_range(
            trade.symbol, "M1", t_created, t_created + timedelta(seconds=59)
        )
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

    def analyze_blocked_signals(self, start_time: datetime) -> list[BlockedSignalQuality]:
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
    ) -> BlockedSignalQuality | None:
        """
        Calculate MFE, MAE, and potential PnL for a rejected signal.
        """
        if not self.connector:
            return None

        # Ensure start_time is timezone-aware before any operations
        start_time = signal.timestamp
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=UTC)

        # Fetch data from signal time until 24 hours later or now
        end_time = min(datetime.now(UTC), start_time + timedelta(hours=24))

        df = self.connector.get_rates_range(signal.symbol, "M5", start_time, end_time)
        if df.empty:
            # Fallback to get_rates if range returns nothing (e.g. connector issues)
            df = self.connector.get_rates(signal.symbol, "M5", 200)

        if df.empty:
            return None

        # Filter bars that happened AFTER the signal
        if df["time"].dt.tz is None:
            df["time"] = df["time"].dt.tz_localize(UTC)

        df = df[df["time"] >= start_time]
        if df.empty:
            return None

        # Calculate excursions
        prices = df["close"].values
        highs = df["high"].values
        lows = df["low"].values

        if signal.direction > 0:  # BUY
            mfe = np.max(highs) - signal.entry_price
            mae = signal.entry_price - np.min(lows)

            # Check if TP or SL would hit first
            would_win = False
            for h_val, l_val in zip(highs, lows, strict=False):
                if h_val >= (signal.take_profit or float("inf")):
                    would_win = True
                    break
                if l_val <= (signal.stop_loss or float("-inf")):
                    would_win = False
                    break

            contract_size = self._get_contract_size(signal.symbol)
            opp_cost = (prices[-1] - signal.entry_price) * signal.lot_size * contract_size
        else:  # SELL
            mfe = signal.entry_price - np.min(lows)
            mae = np.max(highs) - signal.entry_price

            # Check if TP or SL would hit first
            would_win = False
            for h_val, l_val in zip(highs, lows, strict=False):
                if l_val <= (signal.take_profit or float("-inf")):
                    would_win = True
                    break
                if h_val >= (signal.stop_loss or float("inf")):
                    would_win = False
                    break

            contract_size = self._get_contract_size(signal.symbol)
            opp_cost = (signal.entry_price - prices[-1]) * signal.lot_size * contract_size

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

        start_time = datetime.now(UTC) - timedelta(days=days)

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
                    avg_edge_capture=0.0,
                    avg_timing_efficiency=0.0,
                    avg_alpha_decay=0.0,
                    execution_efficiency_score=0.0,
                    rejected_signal_count=len(blocked),
                    executed_trade_count=0,
                )

            avg_slippage = np.mean([q.slippage_pips for q in qualities])
            avg_latency = np.mean([q.execution_latency_ms for q in qualities])
            avg_fill = np.mean([q.fill_quality_score for q in qualities])
            avg_edge = np.mean([q.edge_capture for q in qualities])
            avg_timing = np.mean([q.timing_efficiency for q in qualities])
            avg_alpha = np.mean([q.alpha_decay_pips for q in qualities])

            # Execution efficiency score is a weighted blend
            eff_score = (avg_fill * 0.7) + (max(0.0, 1.0 - (avg_latency / 5000.0)) * 0.3)

            return ExecutionSummary(
                avg_slippage=float(avg_slippage),
                avg_latency_ms=float(avg_latency),
                total_opportunity_cost=float(sum(b.opportunity_cost_pnl for b in blocked)),
                avg_fill_quality=float(avg_fill),
                avg_edge_capture=float(avg_edge),
                avg_timing_efficiency=float(avg_timing),
                avg_alpha_decay=float(avg_alpha),
                execution_efficiency_score=float(eff_score),
                rejected_signal_count=len(blocked),
                executed_trade_count=len(qualities),
            )
