"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/analytics/execution_quality.py
Execution efficiency and trade quality analytics.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, time, timedelta
from typing import Any

import numpy as np
from pydantic import BaseModel, Field
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.trade_logger import (
    Base,
    BlockedSignalAnalysis,
    ExecutionQuality,
    ModelSignal,
    RiskEvent,
    Trade,
)
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
    session: str = Field(..., description="Market session (Asian, London, NY)")
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
    broker_slippage_pips: float = Field(
        ..., description="Pure broker slippage (total slippage minus alpha decay)"
    )
    effective_spread_pips: float = Field(..., description="Realized spread at time of fill")
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
    max_adverse_excursion: float = Field(
        ..., description="Max adverse price movement after signal"
    )
    would_have_won: bool = Field(..., description="True if signal would have hit TP before SL")


class ExecutionSummary(BaseModel):
    """Aggregate execution analytics."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    avg_slippage: float
    avg_broker_slippage: float
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
                name="Broker Slippage",
                value=f"{self.avg_broker_slippage:.2f} pips",
                status="OK" if abs(self.avg_broker_slippage) < 0.5 else "WARNING",
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
            if props:
                if props.get("pip_size"):
                    return float(props["pip_size"])
                if "digits" in props:
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
            if props:
                if props.get("trade_contract_size"):
                    return float(props["trade_contract_size"])
                if props.get("contract_size"):
                    return float(props["contract_size"])

        if any(x in symbol for x in ["XAUUSD", "GOLD"]):
            return 100.0
        return 100000.0

    def analyze_trade(self, trade_id: int, persist: bool = False) -> TradeExecutionQuality | None:
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
            t_created = (
                trade.created_at.replace(tzinfo=UTC)
                if trade.created_at.tzinfo is None
                else trade.created_at
            )
            s_timestamp = (
                signal.timestamp.replace(tzinfo=UTC)
                if signal.timestamp.tzinfo is None
                else signal.timestamp
            )
            latency_td = t_created - s_timestamp
            latency_ms = max(0.0, latency_td.total_seconds() * 1000.0)

            # 3. Spread calculation
            spread_info = self._get_execution_spread(trade)
            spread_pips = spread_info["spread_pips"]

            # 4. Alpha Decay calculation
            alpha_decay = self.calculate_alpha_decay(trade, signal)

            # 5. Broker Slippage (Isolated execution mechanic drag)
            broker_slippage = slippage_pips - alpha_decay

            # 6. Fill quality (0.0 to 1.0)
            # Use broker slippage for a more accurate mechanic evaluation
            slippage_ratio = (
                abs(broker_slippage) / spread_pips if spread_pips > 0.1 else abs(broker_slippage)
            )
            fill_quality = 1.0 / (1.0 + np.exp(slippage_ratio - 2.0))
            fill_quality *= max(0.0, 1.0 - (latency_ms / 10000.0))

            # 7. Drift and Edge Capture
            markout_horizons = [1, 5, 15, 30, 60]
            markouts = self.calculate_markouts(
                symbol, trade.created_at, trade.entry_price, trade.direction, markout_horizons
            )
            edge_capture = self.calculate_edge_capture(trade, signal)

            # 8. Timing Efficiency and Session
            timing_eff = self._calculate_timing_efficiency(trade)
            market_session = self._get_market_session(trade.created_at)

            # 9. Total Execution Cost
            execution_cost = abs(slippage_pips) + (spread_pips / 2.0)

            quality = TradeExecutionQuality(
                trade_id=trade.id,
                ticket=trade.ticket,
                symbol=symbol,
                slippage_pips=float(slippage_pips),
                execution_latency_ms=float(latency_ms),
                fill_quality_score=float(fill_quality),
                edge_capture=float(edge_capture),
                session=market_session,
                post_entry_drift_5m=float(markouts.get("5m", 0.0)),
                post_entry_drift_15m=float(markouts.get("15m", 0.0)),
                timing_efficiency=float(timing_eff),
                spread_at_execution=float(spread_pips),
                slippage_to_spread_ratio=float(slippage_ratio),
                alpha_decay_pips=float(alpha_decay),
                broker_slippage_pips=float(broker_slippage),
                effective_spread_pips=float(spread_pips),
                execution_cost_pips=float(execution_cost),
                markout_pnls=markouts,
            )

            if persist:
                self.save_execution_quality(quality)

            return quality

    def calculate_markouts(
        self,
        symbol: str,
        entry_time: datetime,
        entry_price: float,
        direction: int,
        horizons: list[int],
    ) -> dict[str, float]:
        """Calculate price drift at various horizons (in minutes) after entry."""
        if not self.connector or not horizons:
            return {}

        if entry_time.tzinfo is None:
            entry_time = entry_time.replace(tzinfo=UTC)

        pip_size = self._get_pip_size(symbol)
        max_horizon = max(horizons)
        end_time = entry_time + timedelta(minutes=max_horizon + 2)
        df = self.connector.get_rates_range(symbol, "M1", entry_time, end_time)

        if df.empty:
            return {f"{h}m": 0.0 for h in horizons}

        if df["time"].dt.tz is None:
            df["time"] = df["time"].dt.tz_localize(UTC)

        results = {}
        for h in horizons:
            target_time = entry_time + timedelta(minutes=h)
            mask = df["time"] >= target_time
            if mask.any():
                later_price = df[mask].iloc[0]["close"]
            else:
                later_price = df.iloc[-1]["close"]

            drift = (later_price - entry_price) * direction
            results[f"{h}m"] = float(drift / pip_size)

        return results

    def calculate_alpha_decay(self, trade: Trade, signal: ModelSignal) -> float:
        """Measure price movement between signal and execution."""
        if not self.connector:
            return 0.0

        pip_size = self._get_pip_size(trade.symbol)
        t_created = (
            trade.created_at.replace(tzinfo=UTC)
            if trade.created_at.tzinfo is None
            else trade.created_at
        )
        s_timestamp = (
            signal.timestamp.replace(tzinfo=UTC)
            if signal.timestamp.tzinfo is None
            else signal.timestamp
        )

        try:
            ticks = self.connector.get_ticks_range(trade.symbol, s_timestamp, t_created)
            if not ticks.empty and len(ticks) >= 2:
                start_mid = (ticks.iloc[0]["bid"] + ticks.iloc[0]["ask"]) / 2.0
                end_mid = (ticks.iloc[-1]["bid"] + ticks.iloc[-1]["ask"]) / 2.0
                market_move = (end_mid - start_mid) * signal.direction
                return float(market_move / pip_size)
        except Exception:
            logger.debug("Tick data fallback to M1 for alpha decay")

        df = self.connector.get_rates_range(trade.symbol, "M1", s_timestamp, t_created)
        if df.empty or len(df) < 2:
            return 0.0

        market_move = (df.iloc[-1]["close"] - df.iloc[0]["open"]) * signal.direction
        return float(market_move / pip_size)

    def calculate_edge_capture(self, trade: Trade, signal: ModelSignal) -> float:
        """Measure realized edge vs theoretical edge."""
        if not trade.exit_price or not signal.take_profit:
            return 0.0

        pip_size = self._get_pip_size(trade.symbol)
        spread_info = self._get_execution_spread(trade)
        half_spread_pips = spread_info["spread_pips"] / 2.0

        theoretical_move = abs(signal.take_profit - signal.entry_price)
        realized_move = (trade.exit_price - trade.entry_price) * trade.direction

        if theoretical_move == 0:
            return 0.0

        adjusted_realized = (realized_move / pip_size) - half_spread_pips
        theoretical_pips = theoretical_move / pip_size

        return float(np.clip(adjusted_realized / theoretical_pips, 0.0, 1.2))

    def _get_execution_spread(self, trade: Trade) -> dict[str, float]:
        """Estimate spread at the time of execution."""
        if not self.connector:
            return {"spread_pips": 0.0}

        pip_size = self._get_pip_size(trade.symbol)
        t_created = (
            trade.created_at.replace(tzinfo=UTC)
            if trade.created_at.tzinfo is None
            else trade.created_at
        )

        try:
            ticks = self.connector.get_ticks_range(
                trade.symbol, t_created - timedelta(seconds=10), t_created + timedelta(seconds=10)
            )
            if not ticks.empty:
                avg_spread = (ticks["ask"] - ticks["bid"]).mean()
                return {"spread_pips": float(avg_spread / pip_size)}
        except Exception:
            pass

        df = self.connector.get_rates_range(
            trade.symbol, "M1", t_created - timedelta(minutes=1), t_created
        )
        if df.empty:
            return {"spread_pips": 2.0}

        props = self.connector.get_symbol_properties(trade.symbol)
        point_size = props.get("point") if props else 0.01 if "XAUUSD" in trade.symbol else 0.00001
        avg_spread_points = df["spread"].mean()
        spread_pips = (avg_spread_points * point_size) / pip_size

        return {"spread_pips": float(spread_pips)}

    def _get_market_session(self, dt: datetime) -> str:
        """Identify market session."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        t = dt.time()
        if time(13, 0) <= t <= time(17, 0):
            return "London-NY"
        if time(8, 0) <= t <= time(13, 0):
            return "London"
        if time(17, 0) <= t <= time(22, 0):
            return "NY"
        if time(0, 0) <= t <= time(8, 0):
            return "Asian"
        return "Late-NY"

    def save_blocked_analysis(self, analysis: BlockedSignalQuality) -> None:
        """Persist blocked signal analysis."""
        with self.Session() as session:
            existing = (
                session.query(BlockedSignalAnalysis)
                .filter(BlockedSignalAnalysis.signal_id == analysis.signal_id)
                .first()
            )
            if existing:
                existing.opportunity_cost_pnl = analysis.opportunity_cost_pnl
                existing.max_favorable_excursion = analysis.max_favorable_excursion
                existing.max_adverse_excursion = analysis.max_adverse_excursion
                existing.would_have_won = analysis.would_have_won
                existing.rejection_reason = analysis.rejection_reason
            else:
                db_record = BlockedSignalAnalysis(
                    signal_id=analysis.signal_id,
                    opportunity_cost_pnl=analysis.opportunity_cost_pnl,
                    max_favorable_excursion=analysis.max_favorable_excursion,
                    max_adverse_excursion=analysis.max_adverse_excursion,
                    would_have_won=analysis.would_have_won,
                    rejection_reason=analysis.rejection_reason,
                )
                session.add(db_record)
            session.commit()

    def save_execution_quality(self, quality: TradeExecutionQuality) -> None:
        """Persist execution quality metrics."""
        with self.Session() as session:
            existing = (
                session.query(ExecutionQuality)
                .filter(ExecutionQuality.trade_id == quality.trade_id)
                .first()
            )
            if existing:
                existing.slippage_pips = quality.slippage_pips
                existing.execution_latency_ms = quality.execution_latency_ms
                existing.fill_quality_score = quality.fill_quality_score
                existing.edge_capture = quality.edge_capture
                existing.timing_efficiency = quality.timing_efficiency
                existing.alpha_decay_pips = quality.alpha_decay_pips
                existing.broker_slippage_pips = quality.broker_slippage_pips
                existing.effective_spread_pips = quality.effective_spread_pips
                existing.execution_cost_pips = quality.execution_cost_pips
                existing.session = quality.session
                existing.markout_data = json.dumps(quality.markout_pnls)
            else:
                db_record = ExecutionQuality(
                    trade_id=quality.trade_id,
                    slippage_pips=quality.slippage_pips,
                    execution_latency_ms=quality.execution_latency_ms,
                    fill_quality_score=quality.fill_quality_score,
                    edge_capture=quality.edge_capture,
                    timing_efficiency=quality.timing_efficiency,
                    alpha_decay_pips=quality.alpha_decay_pips,
                    broker_slippage_pips=quality.broker_slippage_pips,
                    effective_spread_pips=quality.effective_spread_pips,
                    execution_cost_pips=quality.execution_cost_pips,
                    session=quality.session,
                    markout_data=json.dumps(quality.markout_pnls),
                )
                session.add(db_record)
            session.commit()

    def _calculate_timing_efficiency(self, trade: Trade) -> float:
        """Determine if entry was at a local extreme of the entry candle."""
        if not self.connector:
            return 0.5
        t_created = (
            trade.created_at.replace(tzinfo=UTC)
            if trade.created_at.tzinfo is None
            else trade.created_at
        )
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
        if trade.direction > 0:
            efficiency = (high - trade.entry_price) / range_val
        else:
            efficiency = (trade.entry_price - low) / range_val
        return float(np.clip(efficiency, 0.0, 1.0))

    def analyze_blocked_signals(
        self, start_time: datetime, persist: bool = False
    ) -> list[BlockedSignalQuality]:
        """Evaluate opportunity cost of rejected signals."""
        results = []
        with self.Session() as session:
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
                signal = session.query(ModelSignal).filter(ModelSignal.id == event.signal_id).first()
                if not signal or signal.trade:
                    continue
                analysis = self._evaluate_opportunity_cost(signal, event.description)
                if analysis:
                    results.append(analysis)
                    if persist:
                        self.save_blocked_analysis(analysis)
        return results

    def _evaluate_opportunity_cost(
        self, signal: ModelSignal, reason: str
    ) -> BlockedSignalQuality | None:
        """Calculate MFE, MAE, and potential PnL for a rejected signal."""
        if not self.connector:
            return None
        start_time = signal.timestamp.replace(tzinfo=UTC) if signal.timestamp.tzinfo is None else signal.timestamp
        end_time = min(datetime.now(UTC), start_time + timedelta(hours=24))
        df = self.connector.get_rates_range(signal.symbol, "M5", start_time, end_time)
        if df.empty:
            df = self.connector.get_rates(signal.symbol, "M5", 200)
        if df.empty:
            return None
        if df["time"].dt.tz is None:
            df["time"] = df["time"].dt.tz_localize(UTC)
        df = df[df["time"] >= start_time]
        if df.empty:
            return None
        prices, highs, lows = df["close"].values, df["high"].values, df["low"].values

        would_win = False
        if signal.direction > 0: # BUY
            mfe, mae = np.max(highs) - signal.entry_price, signal.entry_price - np.min(lows)
            for h_val, l_val in zip(highs, lows, strict=False):
                if h_val >= (signal.take_profit or float("inf")):
                    would_win = True
                    break
                if l_val <= (signal.stop_loss or float("-inf")):
                    would_win = False
                    break
            contract_size = self._get_contract_size(signal.symbol)
            opp_cost = (prices[-1] - signal.entry_price) * signal.lot_size * contract_size
        else: # SELL
            mfe, mae = signal.entry_price - np.min(lows), np.max(highs) - signal.entry_price
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

    def run_batch_analysis(self, days: int = 30, persist: bool = True) -> int:
        """Analyze all un-analyzed trades from the last N days."""
        start_time = datetime.now(UTC) - timedelta(days=days)
        count = 0
        with self.Session() as session:
            trades = (
                session.query(Trade)
                .filter(Trade.created_at >= start_time, Trade.is_deleted.is_(False))
                .all()
            )
            for trade in trades:
                existing = (
                    session.query(ExecutionQuality)
                    .filter(ExecutionQuality.trade_id == trade.id)
                    .first()
                )
                if not existing:
                    if self.analyze_trade(trade.id, persist=persist):
                        count += 1
        return count

    def generate_summary_report(self, days: int = 7, persist: bool = False) -> ExecutionSummary:
        """Aggregate execution quality metrics into a summary report."""
        start_time = datetime.now(UTC) - timedelta(days=days)
        with self.Session() as session:
            trades = session.query(Trade).filter(Trade.created_at >= start_time).all()
            qualities = [self.analyze_trade(t.id, persist=persist) for t in trades]
            qualities = [q for q in qualities if q]
            blocked = self.analyze_blocked_signals(start_time, persist=persist)
            if not qualities:
                return ExecutionSummary(
                    avg_slippage=0.0, avg_broker_slippage=0.0, avg_latency_ms=0.0,
                    total_opportunity_cost=sum(b.opportunity_cost_pnl for b in blocked),
                    avg_fill_quality=0.0, avg_edge_capture=0.0, avg_timing_efficiency=0.0,
                    avg_alpha_decay=0.0, execution_efficiency_score=0.0,
                    rejected_signal_count=len(blocked), executed_trade_count=0
                )
            avg_slippage = np.mean([q.slippage_pips for q in qualities])
            avg_broker = np.mean([q.broker_slippage_pips for q in qualities])
            avg_latency = np.mean([q.execution_latency_ms for q in qualities])
            avg_fill = np.mean([q.fill_quality_score for q in qualities])
            avg_edge = np.mean([q.edge_capture for q in qualities])
            avg_timing = np.mean([q.timing_efficiency for q in qualities])
            avg_alpha = np.mean([q.alpha_decay_pips for q in qualities])
            eff_score = (avg_fill * 0.7) + (max(0.0, 1.0 - (avg_latency / 5000.0)) * 0.3)
            return ExecutionSummary(
                avg_slippage=float(avg_slippage), avg_broker_slippage=float(avg_broker),
                avg_latency_ms=float(avg_latency),
                total_opportunity_cost=float(sum(b.opportunity_cost_pnl for b in blocked)),
                avg_fill_quality=float(avg_fill), avg_edge_capture=float(avg_edge),
                avg_timing_efficiency=float(avg_timing), avg_alpha_decay=float(avg_alpha),
                execution_efficiency_score=float(eff_score),
                rejected_signal_count=len(blocked), executed_trade_count=len(qualities)
            )
