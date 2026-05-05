"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/analytics/journal_mining.py
Trade journal pattern mining and behavioral analysis.
Author : triqbit
License: MIT
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import numpy as np
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
    impacted_algorithms: list[str]
    weak_state_correlation: float = 0.0


class SignalMotif(BaseModel):
    """A recurring combination of signal attributes."""

    algorithm: str
    direction: int
    volatility_bucket: str
    confidence_bucket: str
    session: str = "Unknown"
    frequency: int
    win_rate: float
    cluster_frequency: int = 0


class JournalReport(BaseModel):
    """Final analytical report from journal mining."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    session_analysis: list[SessionAnalysis]
    volatility_patterns: list[VolatilityPattern]
    drawdown_clusters: list[DrawdownCluster]
    profitable_concentrations: list[PatternConcentration]
    risk_block_summary: list[BlockReasonSummary]
    recurring_motifs: list[SignalMotif] = Field(default_factory=list)
    pre_drawdown_motifs: list[SignalMotif] = Field(default_factory=list)
    avg_win_duration: float = 0.0
    avg_loss_duration: float = 0.0

    def to_report_section(self) -> Any:
        """Convert results to TradePatternSection for ResearchReporter."""
        from src.research.reporting import (
            BehavioralRisk,
            PatternConcentration as ReportingPattern,
            SignalMotif as ReportingMotif,
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
        losing_motifs = [m for m in self.recurring_motifs if m.win_rate < 0.4 and m.frequency >= 2]
        if losing_motifs:
            m = losing_motifs[0]
            risks.append(
                BehavioralRisk(
                    type="Toxic Motif",
                    description=f"Toxic pattern for {m.algorithm} in {m.session} session: {m.volatility_bucket} volatility, {m.confidence_bucket} confidence (WR: {m.win_rate:.1%}, Freq: {m.frequency}).",
                )
            )

        # Early Warning Motifs
        if self.pre_drawdown_motifs:
            m = self.pre_drawdown_motifs[0]
            risks.append(
                BehavioralRisk(
                    type="Early Warning",
                    description=f"Pattern '{m.algorithm}' frequently precedes drawdowns (detected {m.frequency} times).",
                )
            )

        primary_insight = "Strategy shows consistent performance across most sessions."
        if risks:
            risk_types = sorted(list(set(r.type for r in risks)))
            primary_insight = f"Critical behavioral risks identified: {', '.join(risk_types)}."

        # Convert SignalMotif internal models to Reporting SignalMotif
        reporting_motifs = []
        for m in self.recurring_motifs[:5]:
            reporting_motifs.append(
                ReportingMotif(
                    algorithm=m.algorithm,
                    direction=m.direction,
                    volatility_bucket=m.volatility_bucket,
                    confidence_bucket=m.confidence_bucket,
                    session=m.session,
                    frequency=m.frequency,
                    win_rate=m.win_rate,
                    cluster_frequency=m.cluster_frequency,
                )
            )

        return TradePatternSection(
            primary_insight=primary_insight,
            concentrations=concentrations[:5],  # Top 5 for clarity
            behavioral_risks=risks,
            motifs=reporting_motifs,
            avg_win_duration=self.avg_win_duration,
            avg_loss_duration=self.avg_loss_duration,
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

    def _get_session(self, dt: datetime) -> list[str]:
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

    def get_session_stats(self, trades_df: pd.DataFrame) -> list[SessionAnalysis]:
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

    def analyze_volatility_patterns(self, signals_df: pd.DataFrame) -> list[VolatilityPattern]:
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

    def detect_drawdown_clusters(self, trades_df: pd.DataFrame) -> list[DrawdownCluster]:
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

    def find_profitable_patterns(self, trades_df: pd.DataFrame) -> list[PatternConcentration]:
        """Find concentrations of profitable patterns by symbol, algorithm, hour, and day."""
        if trades_df.empty:
            return []

        results = []

        # By Symbol
        if "symbol" in trades_df.columns:
            for symbol in trades_df["symbol"].unique():
                group = trades_df[trades_df["symbol"] == symbol]
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
                        attribute="symbol",
                        value=str(symbol),
                        win_rate=win_rate,
                        profit_factor=profit_factor,
                        total_trades=trade_count,
                    )
                )

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

        # By Day of Week
        trades_df["day_of_week"] = trades_df["created_at"].apply(lambda x: x.strftime("%A"))
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for day in days:
            group = trades_df[trades_df["day_of_week"] == day]
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
                    attribute="day",
                    value=day,
                    win_rate=win_rate,
                    profit_factor=profit_factor,
                    total_trades=trade_count,
                )
            )

        # Multi-attribute: Algorithm + Session
        if "algorithm" in trades_df.columns and "sessions" in trades_df.columns:
            # We need to use the exploded version for sessions
            exploded = trades_df.explode("sessions")
            combos = exploded.groupby(["algorithm", "sessions"])
            for (algo, sess), group in combos:
                trade_count = len(group)
                if trade_count < 2:
                    continue
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
                        attribute="algo_session",
                        value=f"{algo} @ {sess}",
                        win_rate=win_rate,
                        profit_factor=profit_factor,
                        total_trades=trade_count,
                    )
                )

        return sorted(results, key=lambda x: x.profit_factor, reverse=True)

    def analyze_risk_blocks(
        self,
        risk_events_df: pd.DataFrame,
        signals_df: pd.DataFrame,
        trades_df: pd.DataFrame = None,
    ) -> list[BlockReasonSummary]:
        """Summarize recurring risk block reasons with weak state correlation."""
        if risk_events_df.empty:
            return []

        results = []
        counts = risk_events_df["event_type"].value_counts()

        # Calculate weak state correlation if trades are provided
        correlations = {}
        if trades_df is not None and not trades_df.empty:
            correlations = self.analyze_strategy_state_correlation(risk_events_df, trades_df)

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
                    reason=str(reason),
                    count=int(count),
                    impacted_algorithms=impacted_algos,
                    weak_state_correlation=correlations.get(reason, 0.0),
                )
            )

        return results

    def _extract_volatility_bucket(self, volatility: float) -> str:
        """Heuristic for volatility bucket assignment."""
        if pd.isna(volatility):
            return "Unknown"
        if volatility < 0.1:
            return "Low"
        if volatility < 0.3:
            return "Normal"
        if volatility < 0.6:
            return "High"
        return "Extreme"

    def _extract_confidence_bucket(self, confidence: float) -> str:
        """Heuristic for confidence bucket assignment."""
        if pd.isna(confidence):
            return "Unknown"
        if confidence < 0.4:
            return "Low"
        if confidence < 0.7:
            return "Medium"
        if confidence < 0.9:
            return "High"
        return "Extreme"

    def detect_pre_drawdown_motifs(
        self, signals_df: pd.DataFrame, trades_df: pd.DataFrame, window_hours: int = 6
    ) -> list[SignalMotif]:
        """
        Identify signal motifs that frequently occur shortly before a drawdown cluster.
        These are 'early warning' motifs that might indicate a strategy is about to fail.
        """
        if signals_df.empty or trades_df.empty:
            return []

        clusters = self.detect_drawdown_clusters(trades_df)
        if not clusters:
            return []

        # Find signals that occurred within window_hours before any cluster started
        pre_cluster_signals = []
        for cluster in clusters:
            start_window = cluster.start_time - pd.Timedelta(hours=window_hours)
            mask = (signals_df["created_at"] >= start_window) & (
                signals_df["created_at"] < cluster.start_time
            )
            pre_cluster_signals.append(signals_df[mask])

        if not pre_cluster_signals:
            return []

        pre_df = pd.concat(pre_cluster_signals).drop_duplicates(subset=["id"])
        if pre_df.empty:
            return []

        # We can reuse the motif logic on this subset
        return self.find_frequent_motifs(pre_df)

    def find_frequent_motifs(
        self, signals_df: pd.DataFrame, trades_df: pd.DataFrame = None
    ) -> list[SignalMotif]:
        """
        Find recurring motifs in signals, especially focusing on losing combinations.
        If trades_df is provided, it specifically highlights motifs found within drawdown clusters.
        """
        if signals_df.empty or "volatility" not in signals_df.columns:
            return []

        df = signals_df.copy()
        df["vol_bucket"] = df["volatility"].apply(self._extract_volatility_bucket)
        df["conf_bucket"] = (
            df["confidence"].apply(self._extract_confidence_bucket)
            if "confidence" in df.columns
            else "Unknown"
        )
        df["session"] = df["created_at"].apply(lambda x: (self._get_session(x) or ["Unknown"])[0])
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

        df["is_in_cluster"] = df["id"].isin(cluster_signal_ids)

        # Group by algo, direction, vol_bucket, conf_bucket, session
        groups = df.groupby(["algorithm", "direction", "vol_bucket", "conf_bucket", "session"])
        results = []

        for (algo, direction, vol, conf, sess), group in groups:
            freq = len(group)
            if freq < 2:
                continue

            win_rate = group["win"].mean()
            cluster_freq = group["is_in_cluster"].sum()
            results.append(
                SignalMotif(
                    algorithm=str(algo),
                    direction=int(direction),
                    volatility_bucket=str(vol),
                    confidence_bucket=str(conf),
                    session=str(sess),
                    frequency=int(freq),
                    win_rate=float(win_rate),
                    cluster_frequency=int(cluster_freq),
                )
            )

        # Score motifs by toxic potential: low win rate * high frequency
        def toxic_score(m: SignalMotif) -> float:
            return (1.0 - m.win_rate) * np.log1p(m.frequency)

        return sorted(results, key=toxic_score, reverse=True)

    def analyze_trade_durations(self, trades_raw: list[Trade]) -> dict[str, float]:
        """Calculate average win vs loss holding times in minutes."""
        if not trades_raw:
            return {"avg_win_duration": 0.0, "avg_loss_duration": 0.0}

        win_durations = []
        loss_durations = []

        for t in trades_raw:
            if t.status == "CLOSED" and t.exit_price is not None:
                # updated_at is roughly the exit time if not explicitly stored
                duration = (t.updated_at - t.created_at).total_seconds() / 60.0
                if t.pnl > 0:
                    win_durations.append(duration)
                elif t.pnl < 0:
                    loss_durations.append(duration)

        return {
            "avg_win_duration": float(pd.Series(win_durations).mean()) if win_durations else 0.0,
            "avg_loss_duration": float(pd.Series(loss_durations).mean()) if loss_durations else 0.0,
        }

    def analyze_strategy_state_correlation(
        self, risk_events_df: pd.DataFrame, trades_df: pd.DataFrame
    ) -> dict[str, float]:
        """
        Detect if risk blocks increase during 'weak strategy states'.
        Weak state is defined as being within 24 hours of a drawdown cluster.
        """
        if risk_events_df.empty or trades_df.empty:
            return {}

        clusters = self.detect_drawdown_clusters(trades_df)
        if not clusters:
            return dict.fromkeys(risk_events_df["event_type"].unique(), 0.0)

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
            return dict.fromkeys(risk_events_df["event_type"].unique(), 0.0)

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

            # Analyze durations
            durations = self.analyze_trade_durations(trades_raw)

            # Convert to DataFrames
            trades_df = pd.DataFrame(
                [
                    {
                        "id": t.id,
                        "pnl": t.pnl,
                        "symbol": t.symbol,
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

            # Ensure sessions are available for pattern concentration
            if not trades_df.empty:
                trades_df["sessions"] = trades_df["created_at"].apply(self._get_session)

            return JournalReport(
                session_analysis=self.get_session_stats(trades_df),
                volatility_patterns=self.analyze_volatility_patterns(signals_df),
                drawdown_clusters=self.detect_drawdown_clusters(trades_df),
                profitable_concentrations=self.find_profitable_patterns(trades_df),
                risk_block_summary=self.analyze_risk_blocks(risk_df, signals_df, trades_df),
                recurring_motifs=self.find_frequent_motifs(signals_df, trades_df),
                pre_drawdown_motifs=self.detect_pre_drawdown_motifs(signals_df, trades_df),
                avg_win_duration=durations["avg_win_duration"],
                avg_loss_duration=durations["avg_loss_duration"],
            )
