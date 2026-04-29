"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/analytics/journal_mining.py
Analyzes trade journals for overtrading, signal quality, and risk patterns.
"""

from __future__ import annotations

import logging
from datetime import datetime, time, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from sqlalchemy import create_engine
from sqlalchemy.orm import joinedload, sessionmaker

from src.core.trade_logger import ModelSignal, RiskEvent, Trade

logger = logging.getLogger(__name__)


class TradingSession(str, Enum):
    ASIAN = "ASIAN"
    LONDON = "LONDON"
    NEW_YORK = "NEW_YORK"
    OTHER = "OTHER"


class VolatilityCondition(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SessionStats(BaseModel):
    session: TradingSession
    trade_count: int
    win_rate: float
    total_pnl: float
    avg_pnl: float


class VolatilityAnalysis(BaseModel):
    condition: VolatilityCondition
    signal_count: int
    false_positive_rate: float
    avg_confidence: float


class BlockReasonStats(BaseModel):
    reason: str
    count: int
    impact_description: str


class DrawdownCluster(BaseModel):
    size: int
    total_loss: float
    start: datetime
    end: datetime


class ProfitableMotif(BaseModel):
    algorithm: str
    direction: int
    total_pnl: float
    avg_pnl: float
    count: int
    win_rate: float


class JournalPatternReport(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_analysis: List[SessionStats]
    volatility_patterns: List[VolatilityAnalysis]
    drawdown_clusters: List[DrawdownCluster]
    profitable_motifs: List[ProfitableMotif]
    risk_block_analysis: List[BlockReasonStats]


class JournalMiner:
    """
    Analyzes trade history and risk events for institutional-grade pattern mining.
    Turns raw trade journals into actionable strategic intelligence.
    """

    def __init__(self, db_url: str = "sqlite:///trades.db"):
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)

    def _get_sessions(self, dt: datetime) -> List[TradingSession]:
        """Determines the trading sessions based on UTC time."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        t = dt.time()
        sessions = []
        # Asian: 00:00 - 08:00 UTC
        if time(0, 0) <= t < time(8, 0):
            sessions.append(TradingSession.ASIAN)
        # London: 08:00 - 16:00 UTC
        if time(8, 0) <= t < time(16, 0):
            sessions.append(TradingSession.LONDON)
        # New York: 13:00 - 21:00 UTC
        if time(13, 0) <= t < time(21, 0):
            sessions.append(TradingSession.NEW_YORK)

        if not sessions:
            sessions.append(TradingSession.OTHER)
        return sessions

    def analyze_sessions(self, trades: List[Trade]) -> List[SessionStats]:
        """Analyzes performance across different trading sessions to detect overtrading or session-specific edge."""
        data = []
        for t in trades:
            timestamp = getattr(t, "created_at", None) or datetime.now(timezone.utc)
            sessions = self._get_sessions(timestamp)
            for s in sessions:
                data.append({"session": s.value, "pnl": t.pnl or 0.0, "is_win": (t.pnl or 0.0) > 0})

        if not data:
            return []

        df = pd.DataFrame(data)
        stats = []
        for session_type in TradingSession:
            sess_df = df[df["session"] == session_type.value]
            if sess_df.empty:
                continue

            stats.append(
                SessionStats(
                    session=session_type,
                    trade_count=len(sess_df),
                    win_rate=float(sess_df["is_win"].mean()),
                    total_pnl=float(sess_df["pnl"].sum()),
                    avg_pnl=float(sess_df["pnl"].mean()),
                )
            )
        return stats

    def analyze_volatility(self, signals: List[ModelSignal]) -> List[VolatilityAnalysis]:
        """
        Analyzes signal quality under different volatility conditions.
        Uses proxy: abs(entry_price - stop_loss) / 2
        """
        data = []
        for s in signals:
            if s.entry_price is not None and s.stop_loss is not None:
                vol_proxy = abs(s.entry_price - s.stop_loss) / 2
                # Bucketing for XAUUSD (Approximate ATR values)
                if vol_proxy < 1.0:
                    cond = VolatilityCondition.LOW
                elif vol_proxy < 3.0:
                    cond = VolatilityCondition.MEDIUM
                else:
                    cond = VolatilityCondition.HIGH

                # False positive: Signal rejected (no trade) or resulting in a loss
                is_false_positive = False
                if not s.trade:
                    is_false_positive = True
                elif s.trade.status == "CLOSED" and (s.trade.pnl or 0.0) <= 0:
                    is_false_positive = True

                data.append(
                    {
                        "condition": cond.value,
                        "is_fp": is_false_positive,
                        "confidence": s.confidence or 0.0,
                    }
                )

        if not data:
            return []

        df = pd.DataFrame(data)
        results = []
        for cond in VolatilityCondition:
            cond_df = df[df["condition"] == cond.value]
            if cond_df.empty:
                continue
            results.append(
                VolatilityAnalysis(
                    condition=cond,
                    signal_count=len(cond_df),
                    false_positive_rate=float(cond_df["is_fp"].mean()),
                    avg_confidence=float(cond_df["confidence"].mean()),
                )
            )
        return results

    def _detect_drawdown_clusters(self, trades: List[Trade]) -> List[DrawdownCluster]:
        """Identifies clusters of consecutive losses to detect strategy degradation."""
        if not trades:
            return []

        trades_sorted = sorted(trades, key=lambda x: x.created_at)
        clusters = []
        current_cluster = []

        def build_cluster(trade_list: List[Trade]) -> DrawdownCluster:
            return DrawdownCluster(
                size=len(trade_list),
                total_loss=sum(tr.pnl or 0.0 for tr in trade_list),
                start=trade_list[0].created_at,
                end=trade_list[-1].created_at,
            )

        for t in trades_sorted:
            if (t.pnl or 0.0) < 0:
                current_cluster.append(t)
            else:
                if len(current_cluster) >= 3:
                    clusters.append(build_cluster(current_cluster))
                current_cluster = []

        if len(current_cluster) >= 3:
            clusters.append(build_cluster(current_cluster))

        return clusters

    def _analyze_profitable_motifs(self, trades: List[Trade]) -> List[ProfitableMotif]:
        """Identifies combinations of algorithm and direction that show strong performance."""
        if not trades:
            return []

        data = []
        for t in trades:
            if t.signal:
                data.append(
                    {
                        "algorithm": t.signal.algorithm or "unknown",
                        "direction": t.signal.direction,
                        "pnl": t.pnl or 0.0,
                        "is_win": (t.pnl or 0.0) > 0,
                    }
                )

        if not data:
            return []

        df = pd.DataFrame(data)
        group = (
            df.groupby(["algorithm", "direction"])
            .agg({"pnl": ["sum", "mean", "count"], "is_win": "mean"})
            .reset_index()
        )

        group.columns = [
            "algorithm",
            "direction",
            "total_pnl",
            "avg_pnl",
            "count",
            "win_rate",
        ]

        # Filter motifs with positive performance and convert to Pydantic models
        profitable = group[group["total_pnl"] > 0]
        return [ProfitableMotif(**row) for _, row in profitable.iterrows()]

    def _analyze_block_reasons(self, events: List[RiskEvent]) -> List[BlockReasonStats]:
        """Analyzes reasons for trade rejections."""
        if not events:
            return []

        counts = {}
        for e in events:
            counts[e.event_type] = counts.get(e.event_type, 0) + 1

        return [
            BlockReasonStats(
                reason=k, count=v, impact_description=f"Blocked {v} potential trades due to {k}"
            )
            for k, v in counts.items()
        ]

    def run_mining_report(self) -> JournalPatternReport:
        """Executes full suite of journal mining analytics."""
        with self.Session() as session:
            # Use joinedload to avoid N+1 queries
            trades = (
                session.query(Trade)
                .options(joinedload(Trade.signal))
                .filter(Trade.status == "CLOSED")
                .all()
            )
            signals = session.query(ModelSignal).options(joinedload(ModelSignal.trade)).all()
            risk_events = session.query(RiskEvent).all()

            return JournalPatternReport(
                session_analysis=self.analyze_sessions(trades),
                volatility_patterns=self.analyze_volatility(signals),
                drawdown_clusters=self._detect_drawdown_clusters(trades),
                profitable_motifs=self._analyze_profitable_motifs(trades),
                risk_block_analysis=self._analyze_block_reasons(risk_events),
            )
