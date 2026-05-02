"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/analytics/journal_mining.py
Trade journal pattern mining and behavioral analysis.
Author : triqbit
License: MIT
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import pandas as pd
from pydantic import BaseModel, Field
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.trade_logger import Base, ModelSignal, RiskEvent, Trade


class SessionAnalysis(BaseModel):
    """Overtrading and performance metrics per trading session."""
    session_name: str
    trade_count: int
    win_rate: float
    profit_factor: float
    is_overtrading: bool = False


class VolatilityPattern(BaseModel):
    """Pattern of false positives under specific volatility regimes."""
    volatility_bucket: str
    signal_count: int
    false_positive_rate: float
    avg_confidence: float


class DrawdownCluster(BaseModel):
    """A cluster of consecutive losing trades."""
    start_time: datetime
    end_time: datetime
    trade_count: int
    total_loss: float


class PatternConcentration(BaseModel):
    """Concentration of profitable or losing patterns."""
    attribute: str
    value: str
    win_rate: float
    profit_factor: float
    total_trades: int


class BlockReasonSummary(BaseModel):
    """Summary of repeated signal block reasons."""
    reason: str
    count: int
    impacted_algorithms: List[str]


class JournalReport(BaseModel):
    """Final analytical report from journal mining."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_analysis: List[SessionAnalysis]
    volatility_patterns: List[VolatilityPattern]
    drawdown_clusters: List[DrawdownCluster]
    profitable_concentrations: List[PatternConcentration]
    risk_block_summary: List[BlockReasonSummary]

    def to_report_section(self) -> Any:
        """Convert results to TradePatternSection for ResearchReporter."""
        from src.research.reporting import (
            BehavioralRisk,
            PatternConcentration as ReportingPattern,
        )
        from src.research.reporting import TradePatternSection

        # Map profitable concentrations
        concentrations = []
        for c in self.profitable_concentrations:
            concentrations.append(
                ReportingPattern(
                    attribute=c.attribute,
                    value=c.value,
                    win_rate=c.win_rate,
                    profit_factor=c.profit_factor,
                )
            )

        # Identify behavioral risks from drawdown clusters and overtrading
        risks = []
        overtrading_sessions = [s.session_name for s in self.session_analysis if s.is_overtrading]
        if overtrading_sessions:
            risks.append(
                BehavioralRisk(
                    type="Overtrading",
                    description=f"High trade frequency detected in sessions: {', '.join(overtrading_sessions)}",
                )
            )

        if len(self.drawdown_clusters) > 0:
            total_loss = sum(c.total_loss for c in self.drawdown_clusters)
            risks.append(
                BehavioralRisk(
                    type="Loss Clustering",
                    description=f"Detected {len(self.drawdown_clusters)} significant drawdown clusters with total loss of {total_loss:.2f}",
                )
            )

        primary_insight = "Strategy shows consistent performance across most sessions."
        if risks:
            primary_insight = f"Behavioral risks identified: {risks[0].type}."

        return TradePatternSection(
            primary_insight=primary_insight,
            concentrations=concentrations[:5],  # Top 5 for clarity
            behavioral_risks=risks,
        )


class JournalMiner:
    """Enterprise pattern recognition engine for trade journals."""

    def __init__(self, db_url: str = "sqlite:///trades.db") -> None:
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.sessions = {
            "Sydney": (22, 7),
            "Tokyo": (0, 9),
            "London": (8, 17),
            "New York": (13, 22),
        }

    def _get_session(self, dt: datetime) -> List[str]:
        """Determine which trading sessions a given UTC time falls into."""
        hour = dt.hour
        active = []
        for name, (start, end) in self.sessions.items():
            if start < end:
                if start <= hour < end:
                    active.append(name)
            else:  # Crosses midnight
                if hour >= start or hour < end:
                    active.append(name)
        return active

    def get_session_stats(self, trades_df: pd.DataFrame) -> List[SessionAnalysis]:
        """Detect overtrading and performance per session."""
        if trades_df.empty:
            return []

        # Expand sessions
        trades_df["sessions"] = trades_df["created_at"].apply(self._get_session)
        exploded = trades_df.explode("sessions")

        results = []
        avg_trades_per_session = len(trades_df) / 4 # Rough heuristic

        for name in self.sessions:
            sess_data = exploded[exploded["sessions"] == name]
            if sess_data.empty:
                results.append(SessionAnalysis(
                    session_name=name,
                    trade_count=0,
                    win_rate=0.0,
                    profit_factor=0.0,
                    is_overtrading=False
                ))
                continue

            trade_count = len(sess_data)
            wins = sess_data[sess_data["pnl"] > 0]
            losses = sess_data[sess_data["pnl"] < 0]
            win_rate = len(wins) / trade_count if trade_count > 0 else 0.0

            gross_profit = wins["pnl"].sum()
            gross_loss = abs(losses["pnl"].sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)

            results.append(SessionAnalysis(
                session_name=name,
                trade_count=trade_count,
                win_rate=win_rate,
                profit_factor=profit_factor,
                is_overtrading=trade_count > (avg_trades_per_session * 1.5)
            ))

        return results

    def analyze_volatility_patterns(self, signals_df: pd.DataFrame) -> List[VolatilityPattern]:
        """Analyze false positives under specific volatility conditions."""
        if signals_df.empty or "volatility" not in signals_df.columns:
            return []

        df = signals_df.dropna(subset=["volatility"])
        if df.empty:
            return []

        # Create buckets for volatility
        try:
            df["bucket"] = pd.qcut(df["volatility"], q=4, labels=["Low", "Normal", "High", "Extreme"], duplicates="drop")
        except ValueError:
            # Fallback if not enough data for qcut
            df["bucket"] = "Standard"

        results = []
        for bucket in df["bucket"].unique():
            group = df[df["bucket"] == bucket]
            signal_count = len(group)

            # A false positive is a signal that was executed but had negative PnL or
            # we can just use the PnL from the joined Trade table if available.
            # Here we assume signals_df is already joined with trades.
            if "pnl" in group.columns:
                false_positives = len(group[group["pnl"] < 0])
                fp_rate = false_positives / signal_count if signal_count > 0 else 0.0
            else:
                fp_rate = 0.0

            results.append(VolatilityPattern(
                volatility_bucket=str(bucket),
                signal_count=signal_count,
                false_positive_rate=fp_rate,
                avg_confidence=float(group["confidence"].mean()) if "confidence" in group.columns else 0.0
            ))

        return results

    def detect_drawdown_clusters(self, trades_df: pd.DataFrame) -> List[DrawdownCluster]:
        """Detect clusters of 3+ consecutive losing trades."""
        if trades_df.empty:
            return []

        trades = trades_df.sort_values("created_at").to_dict("records")
        clusters = []
        current_cluster = []

        for trade in trades:
            if trade["pnl"] < 0:
                current_cluster.append(trade)
            else:
                if len(current_cluster) >= 3:
                    clusters.append(DrawdownCluster(
                        start_time=current_cluster[0]["created_at"],
                        end_time=current_cluster[-1]["created_at"],
                        trade_count=len(current_cluster),
                        total_loss=sum(t["pnl"] for t in current_cluster)
                    ))
                current_cluster = []

        # Check last cluster
        if len(current_cluster) >= 3:
            clusters.append(DrawdownCluster(
                start_time=current_cluster[0]["created_at"],
                end_time=current_cluster[-1]["created_at"],
                trade_count=len(current_cluster),
                total_loss=sum(t["pnl"] for t in current_cluster)
            ))

        return clusters

    def find_profitable_patterns(self, trades_df: pd.DataFrame) -> List[PatternConcentration]:
        """Find concentrations of profitable patterns by algorithm and hour."""
        if trades_df.empty:
            return []

        results = []

        # By Algorithm
        if "algorithm" in trades_df.columns:
            for algo in trades_df["algorithm"].unique():
                group = trades_df[trades_df["algorithm"] == algo]
                trade_count = len(group)
                wins = group[group["pnl"] > 0]
                losses = group[group["pnl"] < 0]
                win_rate = len(wins) / trade_count
                gross_profit = wins["pnl"].sum()
                gross_loss = abs(losses["pnl"].sum())
                profit_factor = gross_profit / gross_loss if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)

                results.append(PatternConcentration(
                    attribute="algorithm",
                    value=str(algo),
                    win_rate=win_rate,
                    profit_factor=profit_factor,
                    total_trades=trade_count
                ))

        # By Hour
        trades_df["hour"] = trades_df["created_at"].apply(lambda x: x.hour)
        for hour in range(24):
            group = trades_df[trades_df["hour"] == hour]
            if group.empty:
                continue

            trade_count = len(group)
            wins = group[group["pnl"] > 0]
            losses = group[group["pnl"] < 0]
            win_rate = len(wins) / trade_count
            gross_profit = wins["pnl"].sum()
            gross_loss = abs(losses["pnl"].sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)

            results.append(PatternConcentration(
                attribute="hour",
                value=f"{hour:02d}:00",
                win_rate=win_rate,
                profit_factor=profit_factor,
                total_trades=trade_count
            ))

        return sorted(results, key=lambda x: x.profit_factor, reverse=True)

    def analyze_risk_blocks(self, risk_events_df: pd.DataFrame, signals_df: pd.DataFrame) -> List[BlockReasonSummary]:
        """Summarize recurring risk block reasons."""
        if risk_events_df.empty:
            return []

        results = []
        counts = risk_events_df["event_type"].value_counts()

        for reason, count in counts.items():
            # Find algorithms impacted by this reason if signal_id is present
            impacted_algos = []
            if not signals_df.empty and "signal_id" in risk_events_df.columns:
                event_signals = risk_events_df[risk_events_df["event_type"] == reason]["signal_id"]
                relevant_signals = signals_df[signals_df["id"].isin(event_signals)]
                if "algorithm" in relevant_signals.columns:
                    impacted_algos = list(relevant_signals["algorithm"].unique())

            results.append(BlockReasonSummary(
                reason=str(reason),
                count=int(count),
                impacted_algorithms=impacted_algos
            ))

        return results

    def run_mining(self) -> JournalReport:
        """Execute full mining suite and return typed report."""
        with self.Session() as session:
            # Fetch data
            trades_raw = session.query(Trade).filter(Trade.is_deleted.is_(False)).all()
            signals_raw = session.query(ModelSignal).filter(ModelSignal.is_deleted.is_(False)).all()
            risk_raw = session.query(RiskEvent).filter(RiskEvent.is_deleted.is_(False)).all()

            # Convert to DataFrames
            trades_df = pd.DataFrame([
                {
                    "id": t.id,
                    "pnl": t.pnl,
                    "created_at": t.created_at,
                    "algorithm": t.signal.algorithm if t.signal else "Unknown"
                } for t in trades_raw
            ])

            signals_df = pd.DataFrame([
                {
                    "id": s.id,
                    "algorithm": s.algorithm,
                    "confidence": s.confidence,
                    "volatility": s.volatility,
                    "pnl": s.trade.pnl if s.trade else None,
                    "created_at": s.created_at
                } for s in signals_raw
            ])

            risk_df = pd.DataFrame([
                {
                    "event_type": r.event_type,
                    "signal_id": r.signal_id
                } for r in risk_raw
            ])

            return JournalReport(
                session_analysis=self.get_session_stats(trades_df),
                volatility_patterns=self.analyze_volatility_patterns(signals_df),
                drawdown_clusters=self.detect_drawdown_clusters(trades_df),
                profitable_concentrations=self.find_profitable_patterns(trades_df),
                risk_block_summary=self.analyze_risk_blocks(risk_df, signals_df)
            )
