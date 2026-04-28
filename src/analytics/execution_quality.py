"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/analytics/execution_quality.py
Measures execution efficiency, slippage, and trade quality to distinguish
alpha quality from execution quality.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np
from pydantic import BaseModel, Field

from src.core.trade_logger import ModelSignal, Trade, TradeLogger

logger = logging.getLogger(__name__)


class SlippageStats(BaseModel):
    """Slippage metrics in price units and percentage."""
    avg_slippage: float = 0.0
    max_slippage: float = 0.0
    slippage_pct: float = 0.0
    negative_slippage_count: int = 0
    positive_slippage_count: int = 0


class FillQuality(BaseModel):
    """Fill quality relative to spread."""
    avg_spread_cost: float = 0.0
    fill_score: float = Field(default=0.0, description="0.0 (poor) to 1.0 (perfect)")
    inside_spread_pct: float = 0.0


class ExecutionMetrics(BaseModel):
    """Comprehensive execution metrics for a period or set of trades."""
    symbol: str
    total_trades: int
    avg_latency_ms: float = 0.0
    slippage: SlippageStats
    fill_quality: FillQuality
    edge_capture: float = Field(default=0.0, description="Spread-adjusted edge capture")
    mfe_avg: float = 0.0  # Max Favorable Excursion
    mae_avg: float = 0.0  # Max Adverse Excursion


class BlockedTradeAnalysis(BaseModel):
    """Analysis of signals that were rejected by risk management."""
    count: int
    hypothetical_pnl: float = 0.0
    rejection_reasons: Dict[str, int]


class TradeQualityReport(BaseModel):
    """Final aggregated report for institutional evaluation."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metrics: Dict[str, ExecutionMetrics]
    blocked_analysis: BlockedTradeAnalysis
    overall_execution_score: float = 0.0


class ExecutionAnalyzer:
    """
    Analyzes trade logs and signals to measure execution efficiency.
    """

    def __init__(self, trade_logger: TradeLogger):
        self.logger_db = trade_logger

    def analyze_period(self, symbol: Optional[str] = None) -> TradeQualityReport:
        """
        Perform full execution quality analysis.
        """
        with self.logger_db.Session() as session:
            # Fetch closed trades
            query = session.query(Trade).filter(Trade.status == "CLOSED")
            if symbol:
                query = query.filter(Trade.symbol == symbol)
            trades = query.all()

            # Fetch rejected signals
            from src.core.trade_logger import RiskEvent
            rejected_events = session.query(RiskEvent).filter(
                RiskEvent.event_type == "SIGNAL_REJECTED"
            ).all()

            metrics_map = {}
            symbols = {t.symbol for t in trades} if not symbol else {symbol}

            for sym in symbols:
                sym_trades = [t for t in trades if t.symbol == sym]
                if not sym_trades:
                    continue
                metrics_map[sym] = self._calculate_metrics(sym, sym_trades)

            blocked_analysis = self._analyze_blocked_signals(session, rejected_events)

            overall_score = 0.0
            if metrics_map:
                overall_score = np.mean([m.fill_quality.fill_score for m in metrics_map.values()])

            return TradeQualityReport(
                metrics=metrics_map,
                blocked_analysis=blocked_analysis,
                overall_execution_score=float(overall_score)
            )

    def _calculate_metrics(self, symbol: str, trades: List[Trade]) -> ExecutionMetrics:
        """Calculate detailed metrics for a set of trades."""
        latencies = [t.execution_latency_ms for t in trades if t.execution_latency_ms is not None]

        slippages = []
        for t in trades:
            if t.requested_price and t.entry_price:
                # Slippage = (Fill Price - Requested Price) * direction
                # For Buy (1): positive slippage is bad (fill > requested)
                # For Sell (-1): positive slippage is bad (fill < requested)
                # Wait, standard definition:
                # Positive slippage: fill better than requested.
                # Negative slippage: fill worse than requested.
                # Buy: requested 2000, fill 1999 -> +1.0 (Good)
                # Buy: requested 2000, fill 2001 -> -1.0 (Bad)
                # Sell: requested 2000, fill 2001 -> +1.0 (Good)
                # Sell: requested 2000, fill 1999 -> -1.0 (Bad)
                slip = (t.requested_price - t.entry_price) * t.direction
                slippages.append(slip)

        slippage_stats = SlippageStats(
            avg_slippage=float(np.mean(slippages)) if slippages else 0.0,
            max_slippage=float(np.min(slippages)) if slippages else 0.0, # min is "most negative"
            negative_slippage_count=len([s for s in slippages if s < 0]),
            positive_slippage_count=len([s for s in slippages if s > 0])
        )

        # Fill Quality
        spread_costs = []
        fill_scores = []
        inside_spread_count = 0
        valid_fill_count = 0

        for t in trades:
            if t.entry_spread and t.entry_spread > 0:
                valid_fill_count += 1
                # Spread cost as percentage of spread
                # If we filled at requested price, and requested was mid, cost is 0.5 * spread.
                # This is simplified without knowing the full book.
                # But we can measure how much slippage we took relative to spread.
                slip = (t.requested_price - t.entry_price) * t.direction if t.requested_price else 0
                cost = (t.entry_spread / 2.0) - slip
                spread_costs.append(cost)

                # Inside spread if slip is better than -entry_spread/2 (assuming requested was mid)
                # or more simply if fill is better than requested.
                if slip >= 0:
                    inside_spread_count += 1

                # Fill score: 1.0 if slip >= 0, scales down as slip becomes negative
                score = max(0.0, min(1.0, 1.0 + (slip / t.entry_spread)))
                fill_scores.append(score)

        fill_quality = FillQuality(
            avg_spread_cost=float(np.mean(spread_costs)) if spread_costs else 0.0,
            fill_score=float(np.mean(fill_scores)) if fill_scores else 0.0,
            inside_spread_pct=(inside_spread_count / valid_fill_count) if valid_fill_count > 0 else 0.0
        )

        # Edge Capture (PnL vs Spread)
        # Standard: (Gross PnL) / (Total Spread paid)
        # Note: contract_size is 100 for XAUUSD.
        contract_size = 100
        total_pnl = sum(t.pnl for t in trades)
        total_spread = sum(
            t.entry_spread * contract_size * t.lot_size
            for t in trades if t.entry_spread
        )
        edge_capture = total_pnl / total_spread if total_spread > 0 else 0.0

        mfes = [t.mfe for t in trades if t.mfe is not None]
        maes = [t.mae for t in trades if t.mae is not None]

        return ExecutionMetrics(
            symbol=symbol,
            total_trades=len(trades),
            avg_latency_ms=float(np.mean(latencies)) if latencies else 0.0,
            slippage=slippage_stats,
            fill_quality=fill_quality,
            edge_capture=float(edge_capture),
            mfe_avg=float(np.mean(mfes)) if mfes else 0.0,
            mae_avg=float(np.mean(maes)) if maes else 0.0
        )

    def _analyze_blocked_signals(self, session, rejected_events) -> BlockedTradeAnalysis:
        """
        Analyze what would have happened if rejected signals were traded.
        This is a 'ghost' pnl analysis.
        """
        hypothetical_pnl = 0.0
        rejection_reasons = {}

        for event in rejected_events:
            reason = event.description or "Unknown"
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1

            # If we have a signal_id, we can look up its performance
            if event.signal_id:
                signal = session.query(ModelSignal).filter(ModelSignal.id == event.signal_id).first()
                if signal:
                    # In a real system, we'd look up the price history after the signal.
                    # For this implementation, we'll look for any trades that happened around that time
                    # or just mark it as "potential".
                    # Since we don't have historical price feed here, we'll keep it as 0.0
                    # or implement a simple proxy if data exists.
                    pass

        return BlockedTradeAnalysis(
            count=len(rejected_events),
            hypothetical_pnl=hypothetical_pnl,
            rejection_reasons=rejection_reasons
        )
