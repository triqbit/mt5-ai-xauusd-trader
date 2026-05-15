"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/analytics/execution_quality.py
Execution efficiency and trade quality analytics.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, time, timedelta
from typing import Any

import numpy as np
import structlog
from pydantic import BaseModel, Field
from sqlalchemy import select

from src.core.database import get_engine, get_session_factory
from src.core.trade_logger import (
    Base,
    BlockedSignalAnalysis,
    ExecutionQuality,
    ModelSignal,
    RiskEvent,
    Trade,
)
from src.trading.mt5_connector import MT5Connector

logger = structlog.get_logger(__name__)


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
    mfe_pips: float = Field(default=0.0, description="Max Favorable Excursion after entry")
    mae_pips: float = Field(default=0.0, description="Max Adverse Excursion after entry")
    implementation_shortfall_pips: float = Field(
        default=0.0, description="Total cost from signal to fill including alpha decay"
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
    avg_broker_slippage: float
    avg_latency_ms: float
    total_opportunity_cost: float
    avg_fill_quality: float
    avg_edge_capture: float
    avg_timing_efficiency: float
    avg_alpha_decay: float
    avg_mfe_trades: float = Field(default=0.0, description="Avg MFE of executed trades")
    avg_mae_trades: float = Field(default=0.0, description="Avg MAE of executed trades")
    execution_efficiency_score: float
    rejected_signal_count: int
    executed_trade_count: int
    avg_mae: float = Field(default=0.0, description="Avg Max Adverse Excursion of blocked signals")
    avg_mfe: float = Field(
        default=0.0, description="Avg Max Favorable Excursion of blocked signals"
    )

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
            ExecutionMetric(
                name="Trade MFE/MAE",
                value=f"{self.avg_mfe_trades:.1f}/{self.avg_mae_trades:.1f} pips",
                status="OK",
            ),
        ]

        return ExecutionQualitySection(
            efficiency_score=float(self.execution_efficiency_score * 100),
            metrics=metrics,
            opportunity_cost=f"${self.total_opportunity_cost:,.2f} (MAE: {self.avg_mae:.2f}, MFE: {self.avg_mfe:.2f})",
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
        self.engine = get_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = get_session_factory(self.engine)
        self.connector = connector

    def _get_pip_size(self, symbol: str) -> float:
        """
        Utility to get pip size for a symbol.
        Leverages connector properties with institutional-standard fallbacks.
        """
        # Static overrides for common institutional symbols (prioritize these)
        symbol_upper = symbol.upper()
        if any(x in symbol_upper for x in ["XAU", "GOLD"]):
            return 0.1
        if any(x in symbol_upper for x in ["JPY", "HUF"]):
            return 0.01
        if any(x in symbol_upper for x in ["BTC", "ETH", "USDT"]):
            return 1.0

        if self.connector:
            try:
                props = self.connector.get_symbol_properties(symbol)
                if props:
                    if props.get("pip_size"):
                        return float(props["pip_size"])
                    if "digits" in props:
                        digits = int(props["digits"])
                        # Standard Forex: 5 digits -> 0.0001 pip, 3 digits -> 0.01 pip
                        return 10 ** -(digits - 1) if digits > 0 else 1.0
            except Exception as e:
                logger.debug("failed_to_get_pip_size_from_connector", symbol=symbol, error=str(e))

        # Static fallbacks for common institutional symbols
        symbol_upper = symbol.upper()
        if any(x in symbol_upper for x in ["XAU", "GOLD"]):
            return 0.1
        if any(x in symbol_upper for x in ["JPY", "HUF"]):
            return 0.01
        if any(x in symbol_upper for x in ["BTC", "ETH", "USDT"]):
            return 1.0
        return 0.0001

    def _get_contract_size(self, symbol: str) -> float:
        """
        Utility to get contract size for a symbol.
        Leverages connector properties with institutional-standard fallbacks.
        """
        if self.connector:
            try:
                props = self.connector.get_symbol_properties(symbol)
                if props:
                    if props.get("trade_contract_size"):
                        return float(props["trade_contract_size"])
                    if props.get("contract_size"):
                        return float(props["contract_size"])
            except Exception as e:
                logger.debug(
                    "failed_to_get_contract_size_from_connector", symbol=symbol, error=str(e)
                )

        # Static fallbacks for common institutional symbols
        symbol_upper = symbol.upper()
        if any(x in symbol_upper for x in ["XAU", "GOLD"]):
            return 100.0
        if any(x in symbol_upper for x in ["BTC", "ETH"]):
            return 1.0
        return 100000.0

    def _get_point_size(self, symbol: str) -> float:
        """Utility to get point size (minimal price change) for a symbol."""
        if self.connector:
            try:
                props = self.connector.get_symbol_properties(symbol)
                if props and props.get("point"):
                    return float(props["point"])
            except Exception:
                pass

        symbol_upper = symbol.upper()
        if any(x in symbol_upper for x in ["XAU", "GOLD"]):
            return 0.01
        if any(x in symbol_upper for x in ["JPY", "HUF"]):
            return 0.001
        if any(x in symbol_upper for x in ["BTC", "ETH"]):
            return 0.01
        return 0.00001

    def analyze_trade(self, trade_id: int, persist: bool = False) -> TradeExecutionQuality | None:
        """
        Analyze execution quality for a specific trade.
        Compares requested signal price vs actual execution price.
        """
        with self.Session() as session:
            trade = session.execute(select(Trade).where(Trade.id == trade_id)).scalar_one_or_none()

            if not trade or not trade.signal:
                logger.warning("trade_or_signal_not_found", trade_id=trade_id)
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
            mid_price = spread_info.get("mid_price", trade.entry_price)

            # 4. Effective Spread (Institutional standard: 2 * |execution - mid|)
            effective_spread = 2.0 * abs(trade.entry_price - mid_price)
            effective_spread_pips = effective_spread / pip_size

            # 5. Alpha Decay calculation
            alpha_decay = self.calculate_alpha_decay(trade, signal)

            # 6. Broker Slippage (Isolated execution mechanic drag)
            broker_slippage = slippage_pips - alpha_decay

            # 7. Fill quality (0.0 to 1.0)
            # Use broker slippage for a more accurate mechanic evaluation
            slippage_ratio = (
                abs(broker_slippage) / spread_pips if spread_pips > 0.1 else abs(broker_slippage)
            )
            fill_quality = 1.0 / (1.0 + np.exp(slippage_ratio - 2.0))
            fill_quality *= max(0.0, 1.0 - (latency_ms / 10000.0))

            # 8. Drift, Excursions and Edge Capture
            markout_horizons = [1, 5, 15, 30, 60]
            excursions = self.calculate_excursions(trade)
            markouts = self.calculate_markouts(
                symbol, trade.created_at, trade.entry_price, trade.direction, markout_horizons
            )
            edge_capture = self.calculate_edge_capture(trade, signal)

            # 9. Timing Efficiency and Session
            timing_eff = self._calculate_timing_efficiency(trade)
            market_session = self._get_market_session(trade.created_at)

            # 10. Total Execution Cost (Slippage + Half effective spread)
            execution_cost = abs(slippage_pips) + (effective_spread_pips / 2.0)

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
                effective_spread_pips=float(effective_spread_pips),
                execution_cost_pips=float(execution_cost),
                mfe_pips=float(excursions.get("mfe", 0.0)),
                mae_pips=float(excursions.get("mae", 0.0)),
                implementation_shortfall_pips=float(slippage_pips + alpha_decay),
                markout_pnls=markouts,
            )

            if persist:
                self.save_execution_quality(quality)

            return quality

    def calculate_excursions(self, trade: Trade) -> dict[str, float]:
        """Calculate MFE and MAE for an executed trade."""
        if not self.connector or not trade.exit_price:
            return {"mfe": 0.0, "mae": 0.0}

        t_entry = (
            trade.created_at.replace(tzinfo=UTC)
            if trade.created_at.tzinfo is None
            else trade.created_at
        )
        # Fallback for updated_at if not set or before entry
        t_exit = (
            trade.updated_at.replace(tzinfo=UTC)
            if trade.updated_at.tzinfo is None
            else trade.updated_at
        )
        if t_exit <= t_entry:
            t_exit = t_entry + timedelta(minutes=5)

        pip_size = self._get_pip_size(trade.symbol)

        try:
            df = self.connector.get_rates_range(trade.symbol, "M1", t_entry, t_exit)
            if not df.empty:
                if trade.direction > 0:  # BUY
                    mfe_price = df["high"].max() - trade.entry_price
                    mae_price = trade.entry_price - df["low"].min()
                else:  # SELL
                    mfe_price = trade.entry_price - df["low"].min()
                    mae_price = df["high"].max() - trade.entry_price

                return {
                    "mfe": float(max(0.0, mfe_price / pip_size)),
                    "mae": float(max(0.0, mae_price / pip_size)),
                }
        except Exception:
            pass

        return {"mfe": 0.0, "mae": 0.0}

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
        point_size = self._get_point_size(symbol)
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
            row = df[mask].iloc[0] if mask.any() else df.iloc[-1]

            # Use mid-price for markout to avoid spread bias
            # MT5 rates usually provide the bid price as 'close'
            price = row["close"]
            if "spread" in row and row["spread"] > 0:
                price += (row["spread"] * point_size) / 2.0

            drift = (price - entry_price) * direction
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
        if df.empty:
            return 0.0

        point_size = self._get_point_size(trade.symbol)

        def get_mid(row):
            price = row["close"]
            if "spread" in row and row["spread"] > 0:
                return price + (row["spread"] * point_size) / 2.0
            return price

        if len(df) >= 2:
            # Use open of first bar to capture movement from the start of the window
            first_bar = df.iloc[0]
            start_price = first_bar["open"]
            if "spread" in first_bar and first_bar["spread"] > 0:
                start_price += (first_bar["spread"] * point_size) / 2.0

            end_mid = get_mid(df.iloc[-1])
            market_move = (end_mid - start_price) * signal.direction
        else:
            # Single bar fallback
            market_move = (df.iloc[0]["close"] - df.iloc[0]["open"]) * signal.direction

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
        """Estimate spread and mid-price at the time of execution."""
        if not self.connector:
            # Methodological fallback: assume entry was at bid/ask edge
            # For a BUY, entry is usually at ASK. Mid = ASK - half_spread
            pip_size = self._get_pip_size(trade.symbol)
            spread_pips = 2.0
            mid_price = trade.entry_price - (trade.direction * (spread_pips * pip_size) / 2.0)
            return {"spread_pips": spread_pips, "mid_price": float(mid_price)}

        pip_size = self._get_pip_size(trade.symbol)
        point_size = self._get_point_size(trade.symbol)
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
                mid_price = ((ticks["ask"] + ticks["bid"]) / 2.0).mean()
                return {
                    "spread_pips": float(avg_spread / pip_size),
                    "mid_price": float(mid_price),
                }
        except Exception:
            pass

        df = self.connector.get_rates_range(
            trade.symbol, "M1", t_created - timedelta(minutes=1), t_created
        )
        if df.empty:
            return {"spread_pips": 2.0, "mid_price": trade.entry_price}

        avg_spread_points = df["spread"].mean()
        spread_pips = (avg_spread_points * point_size) / pip_size
        mid_price = df["close"].iloc[-1] + (avg_spread_points * point_size / 2.0)

        return {"spread_pips": float(spread_pips), "mid_price": float(mid_price)}

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
            existing = session.execute(
                select(BlockedSignalAnalysis).where(
                    BlockedSignalAnalysis.signal_id == analysis.signal_id
                )
            ).scalar_one_or_none()
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
            existing = session.execute(
                select(ExecutionQuality).where(ExecutionQuality.trade_id == quality.trade_id)
            ).scalar_one_or_none()
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
                # Backward-compatible payload: keep horizons at top level
                markout_payload = {
                    **quality.markout_pnls,
                    "mfe_pips": quality.mfe_pips,
                    "mae_pips": quality.mae_pips,
                    "is_pips": quality.implementation_shortfall_pips,
                }
                existing.markout_data = json.dumps(markout_payload)
            else:
                markout_payload = {
                    **quality.markout_pnls,
                    "mfe_pips": quality.mfe_pips,
                    "mae_pips": quality.mae_pips,
                    "is_pips": quality.implementation_shortfall_pips,
                }
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
                    markout_data=json.dumps(markout_payload),
                )
                session.add(db_record)
            session.commit()

    def _calculate_timing_efficiency(self, trade: Trade) -> float:
        """
        Determine if entry was at a local extreme of the execution candle.
        Higher score means better timing (buying near low, selling near high).
        """
        if not self.connector:
            return 0.5
        t_created = (
            trade.created_at.replace(tzinfo=UTC)
            if trade.created_at.tzinfo is None
            else trade.created_at
        )
        # Normalize to start of minute to ensure we fetch the correct candle
        start_of_min = t_created.replace(second=0, microsecond=0)

        df = self.connector.get_rates_range(
            trade.symbol, "M1", start_of_min, start_of_min + timedelta(seconds=59)
        )
        if df.empty:
            # Fallback: try to find the candle containing the timestamp
            df = self.connector.get_rates_range(
                trade.symbol, "M1", t_created - timedelta(minutes=1), t_created
            )

        if df.empty:
            return 0.5

        # Use the candle that actually contains or is closest to our execution time
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
                session.execute(
                    select(RiskEvent).where(
                        RiskEvent.created_at >= start_time,
                        RiskEvent.event_type == "SIGNAL_REJECTED",
                        RiskEvent.signal_id.isnot(None),
                    )
                )
                .scalars()
                .all()
            )

            for event in blocked_events:
                signal = session.execute(
                    select(ModelSignal).where(ModelSignal.id == event.signal_id)
                ).scalar_one_or_none()

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

        # 1. Setup temporal window (max 24h look-ahead)
        start_time = (
            signal.timestamp.replace(tzinfo=UTC)
            if signal.timestamp.tzinfo is None
            else signal.timestamp
        )
        # Give it a bit more time than 24h just in case we need to see the full outcome
        end_time = min(datetime.now(UTC), start_time + timedelta(hours=26))

        # 2. Fetch historical data (prefer M5 for balance of precision and range)
        df = self.connector.get_rates_range(signal.symbol, "M5", start_time, end_time)
        if df.empty:
            # Fallback to recent data if range fetch failed
            df = self.connector.get_rates(signal.symbol, "M5", 500)

        if df.empty:
            logger.warning("historical_data_not_found_for_opportunity_cost", signal_id=signal.id)
            return None

        # 3. Standardize timezone and filter
        if df["time"].dt.tz is None:
            df["time"] = df["time"].dt.tz_localize(UTC)
        else:
            df["time"] = df["time"].dt.tz_convert(UTC)

        df = df[df["time"] >= start_time].copy()
        if df.empty:
            return None

        # 4. Calculate excursions and temporal outcome
        prices, highs, lows = df["close"].values, df["high"].values, df["low"].values
        pip_size = self._get_pip_size(signal.symbol)

        exit_price = prices[-1]
        would_win = False
        if signal.direction > 0:  # BUY
            mfe_price = np.max(highs) - signal.entry_price
            mae_price = signal.entry_price - np.min(lows)
            mfe, mae = mfe_price / pip_size, mae_price / pip_size
            for h_val, l_val in zip(highs, lows, strict=False):
                # If both are hit in same candle, be conservative and assume SL hit first
                hit_tp = signal.take_profit and h_val >= signal.take_profit
                hit_sl = signal.stop_loss and l_val <= signal.stop_loss
                if hit_sl:
                    would_win = False
                    exit_price = signal.stop_loss
                    break
                if hit_tp:
                    would_win = True
                    exit_price = signal.take_profit
                    break
            contract_size = self._get_contract_size(signal.symbol)
            opp_cost = (exit_price - signal.entry_price) * (signal.lot_size or 0.0) * contract_size
        else:  # SELL
            mfe_price = signal.entry_price - np.min(lows)
            mae_price = np.max(highs) - signal.entry_price
            mfe, mae = mfe_price / pip_size, mae_price / pip_size
            for h_val, l_val in zip(highs, lows, strict=False):
                hit_tp = signal.take_profit and l_val <= signal.take_profit
                hit_sl = signal.stop_loss and h_val >= signal.stop_loss
                if hit_sl:
                    would_win = False
                    exit_price = signal.stop_loss
                    break
                if hit_tp:
                    would_win = True
                    exit_price = signal.take_profit
                    break
            contract_size = self._get_contract_size(signal.symbol)
            opp_cost = (signal.entry_price - exit_price) * (signal.lot_size or 0.0) * contract_size

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
                session.execute(
                    select(Trade).where(Trade.created_at >= start_time, Trade.is_deleted.is_(False))
                )
                .scalars()
                .all()
            )

            for trade in trades:
                existing = session.execute(
                    select(ExecutionQuality).where(ExecutionQuality.trade_id == trade.id)
                ).scalar_one_or_none()
                if not existing and self.analyze_trade(trade.id, persist=persist):
                    count += 1
        return count

    def generate_summary_report(self, days: int = 7, persist: bool = False) -> ExecutionSummary:
        """Aggregate execution quality metrics into a summary report."""
        start_time = datetime.now(UTC) - timedelta(days=days)
        with self.Session() as session:
            trades = (
                session.execute(
                    select(Trade).where(Trade.created_at >= start_time, Trade.is_deleted.is_(False))
                )
                .scalars()
                .all()
            )
            qualities = [self.analyze_trade(t.id, persist=persist) for t in trades]
            qualities = [q for q in qualities if q]
            blocked = self.analyze_blocked_signals(start_time, persist=persist)

            avg_mae = np.mean([b.max_adverse_excursion for b in blocked]) if blocked else 0.0
            avg_mfe = np.mean([b.max_favorable_excursion for b in blocked]) if blocked else 0.0

            if not qualities:
                return ExecutionSummary(
                    avg_slippage=0.0,
                    avg_broker_slippage=0.0,
                    avg_latency_ms=0.0,
                    total_opportunity_cost=float(sum(b.opportunity_cost_pnl for b in blocked)),
                    avg_fill_quality=0.0,
                    avg_edge_capture=0.0,
                    avg_timing_efficiency=0.0,
                    avg_alpha_decay=0.0,
                    execution_efficiency_score=0.0,
                    rejected_signal_count=len(blocked),
                    executed_trade_count=0,
                    avg_mae=float(avg_mae),
                    avg_mfe=float(avg_mfe),
                )

            avg_slippage = np.mean([q.slippage_pips for q in qualities])
            avg_broker = np.mean([q.broker_slippage_pips for q in qualities])
            avg_latency = np.mean([q.execution_latency_ms for q in qualities])
            avg_fill = np.mean([q.fill_quality_score for q in qualities])
            avg_edge = np.mean([q.edge_capture for q in qualities])
            avg_timing = np.mean([q.timing_efficiency for q in qualities])
            avg_alpha = np.mean([q.alpha_decay_pips for q in qualities])
            avg_mfe_trades = np.mean([q.mfe_pips for q in qualities])
            avg_mae_trades = np.mean([q.mae_pips for q in qualities])
            eff_score = (avg_fill * 0.7) + (max(0.0, 1.0 - (avg_latency / 5000.0)) * 0.3)

            return ExecutionSummary(
                avg_slippage=float(avg_slippage),
                avg_broker_slippage=float(avg_broker),
                avg_latency_ms=float(avg_latency),
                total_opportunity_cost=float(sum(b.opportunity_cost_pnl for b in blocked)),
                avg_fill_quality=float(avg_fill),
                avg_edge_capture=float(avg_edge),
                avg_timing_efficiency=float(avg_timing),
                avg_alpha_decay=float(avg_alpha),
                avg_mfe_trades=float(avg_mfe_trades),
                avg_mae_trades=float(avg_mae_trades),
                avg_mfe=float(avg_mfe),
                avg_mae=float(avg_mae),
                execution_efficiency_score=float(eff_score),
                rejected_signal_count=len(blocked),
                executed_trade_count=len(qualities),
            )
