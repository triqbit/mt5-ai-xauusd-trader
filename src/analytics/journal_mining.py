"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/analytics/journal_mining.py
Journal mining engine for detecting hidden patterns in executed and rejected trades.
"""

from __future__ import annotations

import logging
from datetime import datetime, time, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.trade_logger import ModelSignal, RiskEvent, Trade

logger = logging.getLogger(__name__)


class SessionAnalysis(BaseModel):
    """Performance metrics broken down by trading session."""

    session_name: str
    trade_count: int
    win_rate: float
    profit_factor: float
    total_pnl: float
    is_overtrading: bool = False


class VolatilityAnalysis(BaseModel):
    """Performance metrics under different volatility conditions."""

    volatility_bucket: str
    trade_count: int
    win_rate: float
    avg_pnl: float


class DrawdownCluster(BaseModel):
    """Detection of clusters of losing trades."""

    start_time: datetime
    end_time: datetime
    trade_count: int
    total_loss: float
    common_algorithms: List[str]


class RejectionAnalysis(BaseModel):
    """Analysis of rejected signals."""

    reason: str
    count: int
    impact_symbol: Optional[str] = None


class JournalReport(BaseModel):
    """Comprehensive journal mining report."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sessions: List[SessionAnalysis]
    volatility_patterns: List[VolatilityAnalysis]
    drawdown_clusters: List[DrawdownCluster]
    rejections: List[RejectionAnalysis]
    profitable_concentrations: List[Dict[str, Any]]
    summary: str


class JournalMiner:
    """
    Analyzes historical trade data and risk events to extract actionable insights.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def analyze_sessions(self) -> List[SessionAnalysis]:
        """Detect overtrading and performance by session (London, NY, Asia)."""
        trades = self.session.query(Trade).filter(Trade.status == "CLOSED").all()
        if not trades:
            return []

        df = pd.DataFrame(
            [
                {
                    "pnl": t.pnl,
                    "hour": t.created_at.hour,
                    "is_win": t.pnl > 0,
                }
                for t in trades
            ]
        )

        def get_session(hour: int) -> str:
            # UTC session boundaries
            if 8 <= hour < 13:
                return "London"
            elif 13 <= hour < 17:
                return "London/NY Overlap"
            elif 17 <= hour < 22:
                return "New York"
            elif 22 <= hour or hour < 8:
                return "Asia/Pacific"
            return "Other"

        df["session"] = df["hour"].apply(get_session)
        session_stats = []

        # Threshold for overtrading (e.g., > 10 trades in a session context)
        # In a real system, this might be based on historical averages.
        overtrading_threshold = 15

        for name, group in df.groupby("session"):
            wins = group["is_win"].sum()
            losses = group["pnl"] < 0
            gross_profit = group[group["pnl"] > 0]["pnl"].sum()
            gross_loss = abs(group[group["pnl"] < 0]["pnl"].sum())
            pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")

            session_stats.append(
                SessionAnalysis(
                    session_name=str(name),
                    trade_count=len(group),
                    win_rate=float(wins / len(group)),
                    profit_factor=float(pf),
                    total_pnl=float(group["pnl"].sum()),
                    is_overtrading=len(group) > overtrading_threshold,
                )
            )

        return session_stats

    def analyze_volatility_patterns(self) -> List[VolatilityAnalysis]:
        """Identify false positives under specific volatility conditions."""
        query = (
            select(Trade, ModelSignal.volatility)
            .join(ModelSignal, Trade.signal_id == ModelSignal.id)
            .where(Trade.status == "CLOSED")
        )
        results = self.session.execute(query).all()
        if not results:
            return []

        data = []
        for trade, vol in results:
            if vol is not None:
                data.append({"pnl": trade.pnl, "volatility": vol})

        if not data:
            return []

        df = pd.DataFrame(data)
        # Simple bucketing: Low, Medium, High based on quantiles
        try:
            df["bucket"] = pd.qcut(
                df["volatility"], q=3, labels=["Low", "Medium", "High"], duplicates="drop"
            )
        except ValueError:
            # Fallback if qcut fails due to lack of unique bin edges
            df["bucket"] = "All"

        vol_stats = []
        for name, group in df.groupby("bucket"):
            vol_stats.append(
                VolatilityAnalysis(
                    volatility_bucket=str(name),
                    trade_count=len(group),
                    win_rate=float((group["pnl"] > 0).mean()),
                    avg_pnl=float(group["pnl"].mean()),
                )
            )
        return vol_stats

    def analyze_drawdown_clusters(self) -> List[DrawdownCluster]:
        """Identify clusters of losing trades (drawdown sequences)."""
        trades = (
            self.session.query(Trade)
            .filter(Trade.status == "CLOSED")
            .order_by(Trade.created_at)
            .all()
        )
        if len(trades) < 3:
            return []

        clusters = []
        current_cluster: List[Trade] = []

        for t in trades:
            if t.pnl < 0:
                current_cluster.append(t)
            else:
                if len(current_cluster) >= 3:
                    # Found a cluster of 3+ losses
                    algs = [
                        t.signal.algorithm for t in current_cluster if t.signal and t.signal.algorithm
                    ]
                    clusters.append(
                        DrawdownCluster(
                            start_time=current_cluster[0].created_at,
                            end_time=current_cluster[-1].created_at,
                            trade_count=len(current_cluster),
                            total_loss=float(sum(t.pnl for t in current_cluster)),
                            common_algorithms=list(set(algs)),
                        )
                    )
                current_cluster = []

        # Handle last cluster
        if len(current_cluster) >= 3:
            algs = [t.signal.algorithm for t in current_cluster if t.signal and t.signal.algorithm]
            clusters.append(
                DrawdownCluster(
                    start_time=current_cluster[0].created_at,
                    end_time=current_cluster[-1].created_at,
                    trade_count=len(current_cluster),
                    total_loss=float(sum(t.pnl for t in current_cluster)),
                    common_algorithms=list(set(algs)),
                )
            )

        return clusters

    def analyze_rejections(self) -> List[RejectionAnalysis]:
        """Analyze repeated block reasons linked to weak strategy states."""
        rejections = self.session.query(RiskEvent).filter(RiskEvent.event_type == "SIGNAL_REJECTED").all()
        if not rejections:
            return []

        df = pd.DataFrame(
            [{"reason": r.description, "symbol": r.symbol} for r in rejections]
        )
        rejection_stats = []
        for (reason, symbol), group in df.groupby(["reason", "symbol"]):
            rejection_stats.append(
                RejectionAnalysis(
                    reason=str(reason),
                    count=len(group),
                    impact_symbol=str(symbol),
                )
            )
        return sorted(rejection_stats, key=lambda x: x.count, reverse=True)

    def analyze_profitable_concentrations(self) -> List[Dict[str, Any]]:
        """Identify concentrations of profitable patterns."""
        query = (
            select(Trade, ModelSignal.algorithm, ModelSignal.direction)
            .join(ModelSignal, Trade.signal_id == ModelSignal.id)
            .where(Trade.status == "CLOSED")
        )
        results = self.session.execute(query).all()
        if not results:
            return []

        data = []
        for trade, algo, direction in results:
            data.append(
                {
                    "pnl": trade.pnl,
                    "algo": algo,
                    "direction": "BUY" if direction == 1 else "SELL",
                }
            )

        df = pd.DataFrame(data)
        concentrations = []
        for (algo, direction), group in df.groupby(["algo", "direction"]):
            if group["pnl"].sum() > 0:
                concentrations.append(
                    {
                        "algorithm": algo,
                        "direction": direction,
                        "total_pnl": float(group["pnl"].sum()),
                        "trade_count": len(group),
                        "win_rate": float((group["pnl"] > 0).mean()),
                    }
                )

        return sorted(concentrations, key=lambda x: x["total_pnl"], reverse=True)

    def generate_report(self) -> JournalReport:
        """Aggregate all insights into a single report."""
        sessions = self.analyze_sessions()
        volatility = self.analyze_volatility_patterns()
        clusters = self.analyze_drawdown_clusters()
        rejections = self.analyze_rejections()
        profitable = self.analyze_profitable_concentrations()

        # Generate a textual summary
        summary = f"Journal Analysis completed at {datetime.now(timezone.utc).isoformat()}.\n"
        summary += f"Analyzed {len(sessions)} sessions and found {len(profitable)} profitable concentrations.\n"
        if any(s.is_overtrading for s in sessions):
            overtrading_sessions = [s.session_name for s in sessions if s.is_overtrading]
            summary += f"WARNING: Overtrading detected in: {', '.join(overtrading_sessions)}.\n"
        if clusters:
            summary += f"DETECTED: {len(clusters)} drawdown clusters (sequences of 3+ losses).\n"

        return JournalReport(
            sessions=sessions,
            volatility_patterns=volatility,
            drawdown_clusters=clusters,
            rejections=rejections,
            profitable_concentrations=profitable,
            summary=summary,
        )
