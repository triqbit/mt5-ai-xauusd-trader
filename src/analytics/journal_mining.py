"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/analytics/journal_mining.py
Trade journal pattern mining and behavioral analysis.
Author : triqbit
License: MIT
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

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
    weak_state_correlation: float = 0.0


class SignalMotif(BaseModel):
    """A recurring combination of signal attributes."""

    algorithm: str
    direction: int
    volatility_bucket: str
    frequency: int
    win_rate: float


class JournalReport(BaseModel):
    """Final analytical report from journal mining."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_analysis: List[SessionAnalysis]
    volatility_patterns: List[VolatilityPattern]
    drawdown_clusters: List[DrawdownCluster]
    profitable_concentrations: List[PatternConcentration]
    risk_block_summary: List[BlockReasonSummary]
    recurring_motifs: List[SignalMotif] = Field(default_factory=list)

    def to_report_section(self) -> Any:
        """Convert results to TradePatternSection for ResearchReporter."""
        from src.research.reporting import (
            BehavioralRisk,
            PatternConcentration as ReportingPattern,
            TradePatternSection,
        )

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

        # High risk block correlation during weak states
        for block in self.risk_block_summary:
            if block.weak_state_correlation > 0.7:
                risks.append(
                    BehavioralRisk(
                        type="Strategy Fragility",
                        description=f"Risk block '{block.reason}' is highly correlated with weak strategy states ({block.weak_state_correlation:.1%}).",
                    )
                )

        # Problematic motifs (recurring losing combinations)
        losing_motifs = [m for m in self.recurring_motifs if m.win_rate < 0.3 and m.frequency >= 3]
        if losing_motifs:
            m = losing_motifs[0]
            risks.append(
                BehavioralRisk(
                    type="Toxic Motif",
                    description=f"Recurring losses detected for {m.algorithm} {m.volatility_bucket} volatility (WR: {m.win_rate:.1%}).",
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
        avg_trades_per_session = len(trades_df) / 4  # Rough heuristic

        for name in self.sessions:
            sess_data = exploded[exploded["sessions"] == name]
            if sess_data.empty:
                results.append(
                    SessionAnalysis(
                        session_name=name,
                        trade_count=0,
                        win_rate=0.0,
                        profit_factor=0.0,
                        is_overtrading=False,
                    )
                )
                continue

            trade_count = len(sess_data)
            wins = sess_data[sess_data["pnl"] > 0]
            losses = sess_data[sess_data["pnl"] < 0]
            win_rate = len(wins) / trade_count if trade_count > 0 else 0.0

            gross_profit = wins["pnl"].sum()
            gross_loss = abs(losses["pnl"].sum())
            profit_factor = (
                gross_profit / gross_loss
                if gross_loss > 0
                else (float("inf") if gross_profit > 0 else 0.0)
            )

            results.append(
                SessionAnalysis(
                    session_name=name,
                    trade_count=trade_count,
                    win_rate=win_rate,
                    profit_factor=profit_factor,
                    is_overtrading=trade_count > (avg_trades_per_session * 1.5),
                )
            )

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
            df["bucket"] = pd.qcut(
                df["volatility"],
                q=4,
                labels=["Low", "Normal", "High", "Extreme"],
                duplicates="drop",
            )
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

            results.append(
                VolatilityPattern(
                    volatility_bucket=str(bucket),
                    signal_count=signal_count,
                    false_positive_rate=fp_rate,
                    avg_confidence=float(group["confidence"].mean())
                    if "confidence" in group.columns
                    else 0.0,
                )
            )

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
                    clusters.append(
                        DrawdownCluster(
                            start_time=current_cluster[0]["created_at"],
                            end_time=current_cluster[-1]["created_at"],
                            trade_count=len(current_cluster),
                            total_loss=sum(t["pnl"] for t in current_cluster),
                        )
                    )
                current_cluster = []

        # Check last cluster
        if len(current_cluster) >= 3:
            clusters.append(
                DrawdownCluster(
                    start_time=current_cluster[0]["created_at"],
                    end_time=current_cluster[-1]["created_at"],
                    trade_count=len(current_cluster),
                    total_loss=sum(t["pnl"] for t in current_cluster),
                )
            )

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
                profit_factor = (
                    gross_profit / gross_loss
                    if gross_loss > 0
                    else (float("inf") if gross_profit > 0 else 0.0)
                )

                results.append(
                    PatternConcentration(
                        attribute="algorithm",
                        value=str(algo),
                        win_rate=win_rate,
                        profit_factor=profit_factor,
                        total_trades=trade_count,
                    )
                )

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
            profit_factor = (
                gross_profit / gross_loss
                if gross_loss > 0
                else (float("inf") if gross_profit > 0 else 0.0)
            )

            results.append(
                PatternConcentration(
                    attribute="hour",
                    value=f"{hour:02d}:00",
                    win_rate=win_rate,
                    profit_factor=profit_factor,
                    total_trades=trade_count,
                )
            )

        return sorted(results, key=lambda x: x.profit_factor, reverse=True)

    def analyze_risk_blocks(
        self, risk_events_df: pd.DataFrame, signals_df: pd.DataFrame
    ) -> List[BlockReasonSummary]:
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

            results.append(
                BlockReasonSummary(
                    reason=str(reason), count=int(count), impacted_algorithms=impacted_algos
                )
            )

        return results

    def _extract_volatility_bucket(self, volatility: float) -> str:
        """Heuristic for volatility bucket assignment."""
        if volatility < 0.1:
            return "Low"
        if volatility < 0.3:
            return "Normal"
        if volatility < 0.6:
            return "High"
        return "Extreme"

    def find_frequent_motifs(
        self, signals_df: pd.DataFrame, trades_df: pd.DataFrame = None
    ) -> List[SignalMotif]:
        """
        Find recurring motifs in signals, especially focusing on losing combinations.
        If trades_df is provided, it specifically highlights motifs found within drawdown clusters.
        """
        if signals_df.empty or "volatility" not in signals_df.columns:
            return []

        df = signals_df.copy()
        df["vol_bucket"] = df["volatility"].apply(self._extract_volatility_bucket)
        df["win"] = df["pnl"] > 0

        # Identify signals in drawdown clusters if trades_df is provided
        cluster_signal_ids = set()
        if trades_df is not None and not trades_df.empty:
            clusters = self.detect_drawdown_clusters(trades_df)
            for cluster in clusters:
                # Find trades in this cluster
                cluster_trades = trades_df[
                    (trades_df["created_at"] >= cluster.start_time)
                    & (trades_df["created_at"] <= cluster.end_time)
                    & (trades_df["pnl"] < 0)
                ]
                if "signal_id" in trades_df.columns:
                    cluster_signal_ids.update(cluster_trades["signal_id"].unique())

        # Group by algo, direction, vol_bucket
        groups = df.groupby(["algorithm", "direction", "vol_bucket"])
        results = []

        for (algo, direction, vol), group in groups:
            freq = len(group)
            if freq < 2:
                continue

            win_rate = group["win"].mean()
            results.append(
                SignalMotif(
                    algorithm=str(algo),
                    direction=int(direction),
                    volatility_bucket=str(vol),
                    frequency=int(freq),
                    win_rate=float(win_rate),
                )
            )

        return sorted(results, key=lambda x: x.win_rate)

    def analyze_strategy_state_correlation(
        self, risk_events_df: pd.DataFrame, trades_df: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Detect if risk blocks increase during 'weak strategy states'.
        Weak state is defined as being within 24 hours of a drawdown cluster.
        """
        if risk_events_df.empty or trades_df.empty:
            return {}

        clusters = self.detect_drawdown_clusters(trades_df)
        if not clusters:
            return {reason: 0.0 for reason in risk_events_df["event_type"].unique()}

        # Mark 'weak' time windows
        weak_windows = []
        for cluster in clusters:
            # Window starts at cluster start and ends 24h after cluster end
            end_time = cluster.end_time + pd.Timedelta(hours=24)
            weak_windows.append((cluster.start_time, end_time))

        def is_weak(dt: datetime) -> bool:
            return any(start <= dt <= end for start, end in weak_windows)

        # Assume risk_events_df has a timestamp. If not, we might need to join with signals
        # Let's check RiskEvent model in trade_logger. It has AuditMixin (created_at)
        if "created_at" not in risk_events_df.columns:
            return {reason: 0.0 for reason in risk_events_df["event_type"].unique()}

        risk_events_df["is_weak_state"] = risk_events_df["created_at"].apply(is_weak)

        results = {}
        for reason in risk_events_df["event_type"].unique():
            group = risk_events_df[risk_events_df["event_type"] == reason]
            if len(group) == 0:
                results[reason] = 0.0
                continue
            weak_count = group["is_weak_state"].sum()
            results[reason] = float(weak_count / len(group))

        return results

    def run_mining(self) -> JournalReport:
        """Execute full mining suite and return typed report."""
        with self.Session() as session:
            # Fetch data
            trades_raw = session.query(Trade).filter(Trade.is_deleted.is_(False)).all()
            signals_raw = session.query(ModelSignal).filter(ModelSignal.is_deleted.is_(False)).all()
            risk_raw = session.query(RiskEvent).filter(RiskEvent.is_deleted.is_(False)).all()

            # Convert to DataFrames
            trades_df = pd.DataFrame(
                [
                    {
                        "id": t.id,
                        "pnl": t.pnl,
                        "created_at": t.created_at,
                        "algorithm": t.signal.algorithm if t.signal else "Unknown",
                        "signal_id": t.signal_id,
                    }
                    for t in trades_raw
                ]
            )

            signals_df = pd.DataFrame(
                [
                    {
                        "id": s.id,
                        "algorithm": s.algorithm,
                        "direction": s.direction,
                        "confidence": s.confidence,
                        "volatility": s.volatility,
                        "pnl": s.trade.pnl if s.trade else None,
                        "created_at": s.created_at,
                    }
                    for s in signals_raw
                ]
            )

            risk_df = pd.DataFrame(
                [
                    {
                        "event_type": r.event_type,
                        "signal_id": r.signal_id,
                        "created_at": r.created_at,
                    }
                    for r in risk_raw
                ]
            )

            # Analyze correlations
            correlations = self.analyze_strategy_state_correlation(risk_df, trades_df)
            risk_blocks = self.analyze_risk_blocks(risk_df, signals_df)
            for block in risk_blocks:
                block.weak_state_correlation = correlations.get(block.reason, 0.0)

            return JournalReport(
                session_analysis=self.get_session_stats(trades_df),
                volatility_patterns=self.analyze_volatility_patterns(signals_df),
                drawdown_clusters=self.detect_drawdown_clusters(trades_df),
                profitable_concentrations=self.find_profitable_patterns(trades_df),
                risk_block_summary=risk_blocks,
                recurring_motifs=self.find_frequent_motifs(signals_df, trades_df),
            )
