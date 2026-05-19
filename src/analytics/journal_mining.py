"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/analytics/journal_mining.py
Trade journal pattern mining and behavioral analysis.
Author : triqbit
License: MIT
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd
import structlog
from pydantic import BaseModel, Field
from sqlalchemy import select

from src.core.database import get_engine, get_session_factory
from src.core.trade_logger import Base, ModelSignal, RiskEvent, Trade

logger = structlog.get_logger(__name__)


class SessionAnalysis(BaseModel):
    """Overtrading and performance metrics per trading session."""

    session_name: str
    trade_count: int
    win_rate: float
    profit_factor: float
    is_overtrading: bool = False
    z_score: float = 0.0


class VolatilityPattern(BaseModel):
    """Pattern of false positives under specific volatility regimes."""

    volatility_bucket: str
    signal_count: int
    false_positive_rate: float
    avg_confidence: float


class PerformanceDecay(BaseModel):
    """Metrics for rolling performance decay."""

    window_size: int
    profit_factor_trend: float
    is_decaying: bool
    recent_pf: float
    baseline_pf: float


class DrawdownCluster(BaseModel):
    """A cluster of consecutive losing trades."""

    start_time: datetime
    end_time: datetime
    trade_count: int
    total_loss: float
    max_equity_drop: float = 0.0


class ProfitCluster(BaseModel):
    """A cluster of consecutive winning trades."""

    start_time: datetime
    end_time: datetime
    trade_count: int
    total_profit: float


class PatternConcentration(BaseModel):
    """Concentration of profitable or losing patterns."""

    attribute: str
    value: str
    win_rate: float
    profit_factor: float
    total_trades: int


class CombinationMotif(BaseModel):
    """A recurring combination of multiple signals within a time window."""

    patterns: list[str]  # e.g. ["ensemble:1", "ppo:-1"]
    frequency: int
    avg_pnl_after: float
    is_toxic: bool = False
    is_golden: bool = False
    expectancy: float = 0.0
    efficiency_ratio: float = 0.0
    session: str = "Mixed"
    volatility_bucket: str = "Mixed"


class BlockReasonSummary(BaseModel):
    """Summary of repeated signal block reasons."""

    reason: str
    count: int
    impacted_algorithms: list[str]
    weak_state_correlation: float = 0.0
    correct_rejection_rate: float = 0.0
    profit_opportunity_cost: float = 0.0


class RejectionQuality(BaseModel):
    """Effectiveness of signal rejections."""

    reason: str
    total_blocked: int
    correct_blocks: int  # avoided losses (would_have_won=False)
    incorrect_blocks: int  # missed profits (would_have_won=True)
    accuracy: float
    profit_opportunity_cost: float


class OverconfidenceEvent(BaseModel):
    """Details of potential overconfidence (aggressive sizing after wins)."""

    trade_id: int
    consecutive_wins: int
    lot_increase_pct: float
    pnl: float


class SignalMotif(BaseModel):
    """A recurring combination of signal attributes."""

    algorithm: str
    direction: int
    volatility_bucket: str
    confidence_bucket: str
    session: str = "Unknown"
    frequency: int
    win_rate: float
    is_toxic: bool = False
    is_golden: bool = False
    expectancy: float = 0.0
    efficiency_ratio: float = 0.0
    cluster_frequency: int = 0


class RevengeTrade(BaseModel):
    """Details of a potential revenge trade (tilt)."""

    trade_id: int
    prev_trade_id: int
    time_diff_min: float
    lot_increase: bool
    pnl: float


class JournalReport(BaseModel):
    """Final analytical report from journal mining."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    session_analysis: list[SessionAnalysis]
    volatility_patterns: list[VolatilityPattern]
    performance_decay: PerformanceDecay | None = None
    drawdown_clusters: list[DrawdownCluster]
    profit_clusters: list[ProfitCluster] = Field(default_factory=list)
    profitable_concentrations: list[PatternConcentration]
    risk_block_summary: list[BlockReasonSummary]
    rejection_quality: list[RejectionQuality] = Field(default_factory=list)
    overconfidence_events: list[OverconfidenceEvent] = Field(default_factory=list)
    recurring_motifs: list[SignalMotif] = Field(default_factory=list)
    pre_drawdown_motifs: list[SignalMotif] = Field(default_factory=list)
    combination_motifs: list[CombinationMotif] = Field(default_factory=list)
    revenge_trades: list[RevengeTrade] = Field(default_factory=list)
    blocked_motifs: list[SignalMotif] = Field(default_factory=list)
    avg_win_duration: float = 0.0
    avg_loss_duration: float = 0.0

    def to_report_section(self) -> Any:
        """Convert results to TradePatternSection for ResearchReporter."""
        from src.research.reporting import (
            BehavioralRisk,
            CombinationMotif as ReportingCombination,
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
                    total_trades=c.total_trades,
                )
            )

        # Identify behavioral risks from drawdown clusters and overtrading
        risks = []
        overtrading_sessions = [s.session_name for s in self.session_analysis if s.is_overtrading]
        if overtrading_sessions:
            risks.append(
                BehavioralRisk(
                    type="Overtrading",
                    description=(
                        f"Statistical overtrading detected in sessions: {', '.join(overtrading_sessions)} "
                        f"(Z-score > {JournalMiner.Z_SCORE_THRESHOLD})."
                    ),
                )
            )

        if len(self.drawdown_clusters) > 0:
            total_loss = sum(c.total_loss for c in self.drawdown_clusters)
            max_drop = max(c.max_equity_drop for c in self.drawdown_clusters)
            risks.append(
                BehavioralRisk(
                    type="Loss Clustering",
                    description=f"Detected {len(self.drawdown_clusters)} drawdown clusters with total loss of {total_loss:.2f} (Max cluster drop: {max_drop:.2f}).",
                )
            )

        if self.performance_decay and self.performance_decay.is_decaying:
            risks.append(
                BehavioralRisk(
                    type="Alpha Decay",
                    description=f"Strategy alpha is decaying: Profit Factor dropped by {abs(self.performance_decay.profit_factor_trend):.1%} over last {self.performance_decay.window_size} trades.",
                )
            )

        if len(self.profit_clusters) > 0:
            total_profit = sum(c.total_profit for c in self.profit_clusters)
            risks.append(
                BehavioralRisk(
                    type="Profit Clustering",
                    description=f"Detected {len(self.profit_clusters)} significant profit clusters with total profit of {total_profit:.2f}",
                )
            )

        # High risk block correlation during weak states
        for block in self.risk_block_summary:
            if block.weak_state_correlation > JournalMiner.WEAK_STATE_CORRELATION:
                risks.append(
                    BehavioralRisk(
                        type="Strategy Fragility",
                        description=f"Risk block '{block.reason}' is highly correlated with weak strategy states ({block.weak_state_correlation:.1%}).",
                    )
                )

        # Problematic motifs (recurring losing combinations)
        losing_motifs = [m for m in self.recurring_motifs if m.is_toxic and m.frequency >= 2]
        if losing_motifs:
            m = losing_motifs[0]
            risks.append(
                BehavioralRisk(
                    type="Toxic Motif",
                    description=f"Toxic pattern for {m.algorithm} in {m.session} session: {m.volatility_bucket} volatility, {m.confidence_bucket} confidence (WR: {m.win_rate:.1%}, Freq: {m.frequency}).",
                )
            )

        # Golden motifs (recurring winning combinations)
        winning_motifs = [m for m in self.recurring_motifs if m.is_golden and m.frequency >= 2]
        if winning_motifs:
            m = winning_motifs[0]
            risks.append(
                BehavioralRisk(
                    type="Golden Motif",
                    description=f"Exceptional pattern for {m.algorithm} in {m.session} session: {m.volatility_bucket} volatility, {m.confidence_bucket} confidence (WR: {m.win_rate:.1%}, Freq: {m.frequency}).",
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

        # Toxic Combinations
        for motif in self.combination_motifs[:3]:
            if motif.is_toxic:
                risks.append(
                    BehavioralRisk(
                        type="Toxic Combination",
                        description=f"Signals {motif.patterns} occurred {motif.frequency} times before drawdowns in {motif.session} session.",
                    )
                )
            elif motif.is_golden:
                risks.append(
                    BehavioralRisk(
                        type="Golden Combination",
                        description=f"Signals {motif.patterns} occurred {motif.frequency} times before profit clusters in {motif.session} session.",
                    )
                )

        # Revenge Trading Risks
        if self.revenge_trades:
            high_lot_revenge = [r for r in self.revenge_trades if r.lot_increase]
            description = f"Detected {len(self.revenge_trades)} potential revenge trades."
            if high_lot_revenge:
                description += f" {len(high_lot_revenge)} involved lot size increases (TILT)."

            risks.append(
                BehavioralRisk(
                    type="Revenge Trading",
                    description=description,
                )
            )

        # Overconfidence Risks
        if self.overconfidence_events:
            risks.append(
                BehavioralRisk(
                    type="Overconfidence",
                    description=f"Detected {len(self.overconfidence_events)} instances of aggressive sizing after wins (GREED).",
                )
            )

        # Rejection Quality Risks
        poor_rejections = [
            r for r in self.rejection_quality if r.accuracy < 0.4 and r.total_blocked >= 3
        ]
        if poor_rejections:
            r = poor_rejections[0]
            risks.append(
                BehavioralRisk(
                    type="Poor Rejection Quality",
                    description=f"Risk block '{r.reason}' has low accuracy ({r.accuracy:.1%}) and missed {r.profit_opportunity_cost:.2f} in profit.",
                )
            )

        # Blocked Golden Motifs (Missed opportunities)
        blocked_golden = [m for m in self.blocked_motifs if m.is_golden and m.frequency >= 2]
        if blocked_golden:
            m = blocked_golden[0]
            risks.append(
                BehavioralRisk(
                    type="Missed Opportunity",
                    description=f"Risk management frequently blocks golden pattern for {m.algorithm} in {m.session} session (Detected {m.frequency} times).",
                )
            )

        # Block Reasons linked to weak strategy states
        # Cluster warning threshold is slightly lower than strict fragility
        for block in self.risk_block_summary:
            if block.weak_state_correlation > (JournalMiner.WEAK_STATE_CORRELATION - 0.1):
                risks.append(
                    BehavioralRisk(
                        type="Cluster Warning",
                        description=f"Block reason '{block.reason}' is highly correlated with weak strategy states ({block.weak_state_correlation:.1%}).",
                    )
                )

        primary_insight = "Strategy shows consistent performance across most sessions."
        if risks:
            risk_types = sorted({r.type for r in risks})
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
                    expectancy=m.expectancy,
                    efficiency_ratio=m.efficiency_ratio,
                    cluster_frequency=m.cluster_frequency,
                )
            )

        # Convert CombinationMotif internal models to Reporting CombinationMotif
        reporting_combinations = []
        for c in self.combination_motifs[:5]:
            reporting_combinations.append(
                ReportingCombination(
                    patterns=c.patterns,
                    frequency=c.frequency,
                    avg_pnl_after=c.avg_pnl_after,
                    is_toxic=c.is_toxic,
                    is_golden=c.is_golden,
                    expectancy=c.expectancy,
                    efficiency_ratio=c.efficiency_ratio,
                    session=c.session,
                    volatility_bucket=c.volatility_bucket,
                )
            )

        return TradePatternSection(
            primary_insight=primary_insight,
            concentrations=concentrations[:5],  # Top 5 for clarity
            behavioral_risks=risks,
            motifs=reporting_motifs,
            combinations=reporting_combinations,
            avg_win_duration=self.avg_win_duration,
            avg_loss_duration=self.avg_loss_duration,
        )


class JournalMiner:
    """
    Enterprise pattern recognition engine for trade journals.

    Analyzes executed and rejected trades to detect behavioral risks, strategy decay,
    and recurring performance motifs. Implements institutional-grade statistical
    checks including Z-score overtrading detection and alpha decay monitoring.
    """

    # Institutional Standard Thresholds
    Z_SCORE_THRESHOLD = 1.5  # Statistical significance for overtrading
    PF_DECAY_THRESHOLD = -0.3  # 30% drop in Profit Factor indicates alpha decay
    WEAK_STATE_CORRELATION = 0.7  # High correlation between blocks and drawdowns
    CONSECUTIVE_WINS_THRESHOLD = 3  # Threshold for checking overconfidence (greed)
    REVENGE_WINDOW_MINS = 30  # Window for detecting tilt/revenge trading
    PRE_DRAWDOWN_WINDOW_HOURS = 24  # Lookback for identifying pre-cluster motifs
    DECAY_WINDOW_SIZE = 20  # Number of trades to check for alpha decay

    def __init__(self, db_url: str = "sqlite:///trades.db") -> None:
        self.engine = get_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = get_session_factory(self.engine)
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
            if (start < end and start <= hour < end) or (
                start >= end and (hour >= start or hour < end)
            ):
                active.append(name)
        return active

    def get_session_stats(self, trades_df: pd.DataFrame) -> list[SessionAnalysis]:
        """
        Detect overtrading and performance per session using Z-score statistics.

        Identifies sessions with statistically significant higher trade frequency than average,
        which often correlates with impulsive behavior or 'revenge' sessions.
        """
        if trades_df.empty:
            return []

        # Expand sessions
        trades_df["sessions"] = trades_df["created_at"].apply(self._get_session)
        exploded = trades_df.explode("sessions")

        results = []

        # Calculate session trade counts for Z-score
        session_counts = []
        for name in self.sessions:
            session_counts.append(len(exploded[exploded["sessions"] == name]))

        mean_trades = np.mean(session_counts)
        std_trades = np.std(session_counts) if len(session_counts) > 1 else 0.0

        for name in self.sessions:
            sess_data = exploded[exploded["sessions"] == name]
            trade_count = len(sess_data)

            # Calculate Z-score for overtrading detection
            z_score = (trade_count - mean_trades) / std_trades if std_trades > 0 else 0.0

            if sess_data.empty:
                results.append(
                    SessionAnalysis(
                        session_name=name,
                        trade_count=0,
                        win_rate=0.0,
                        profit_factor=0.0,
                        is_overtrading=False,
                        z_score=z_score,
                    )
                )
                continue

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

            # Institutional standard: Z-score > Z_SCORE_THRESHOLD indicates significant overtrading
            results.append(
                SessionAnalysis(
                    session_name=name,
                    trade_count=trade_count,
                    win_rate=win_rate,
                    profit_factor=profit_factor,
                    is_overtrading=z_score > self.Z_SCORE_THRESHOLD,
                    z_score=z_score,
                )
            )

        return results

    def analyze_volatility_patterns(self, signals_df: pd.DataFrame) -> list[VolatilityPattern]:
        """
        Analyze false positives under specific volatility conditions.

        Categorizes market volatility into buckets and calculates the false positive rate
        of signals to identify regimes where models may be prone to overfitting or noise.
        """
        if signals_df.empty or "volatility" not in signals_df.columns:
            return []

        df = signals_df.dropna(subset=["volatility"]).copy()
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

    def detect_overconfidence(
        self, trades_df: pd.DataFrame, consecutive_wins_threshold: int = CONSECUTIVE_WINS_THRESHOLD
    ) -> list[OverconfidenceEvent]:
        """
        Detect potential 'overconfidence' or greed.
        Defined as lot size increases following a sequence of consecutive wins.

        Args:
            trades_df: DataFrame of executed trades.
            consecutive_wins_threshold: Number of wins before checking for lot increase.

        Returns:
            List of OverconfidenceEvent objects.
        """
        if trades_df.empty or len(trades_df) < consecutive_wins_threshold + 1:
            return []

        df = trades_df.sort_values("created_at").copy()
        events = []
        consecutive_wins = 0

        for i in range(len(df)):
            trade = df.iloc[i]

            if i > 0 and consecutive_wins >= consecutive_wins_threshold:
                prev_trade = df.iloc[i - 1]
                if (
                    "lot_size" in trade
                    and "lot_size" in prev_trade
                    and trade["lot_size"] > prev_trade["lot_size"]
                    and prev_trade["lot_size"] > 0
                ):
                    lot_inc = (trade["lot_size"] - prev_trade["lot_size"]) / prev_trade["lot_size"]
                    events.append(
                        OverconfidenceEvent(
                            trade_id=int(trade["id"]),
                            consecutive_wins=consecutive_wins,
                            lot_increase_pct=float(lot_inc),
                            pnl=float(trade["pnl"]),
                        )
                    )

            if trade["pnl"] > 0:
                consecutive_wins += 1
            else:
                consecutive_wins = 0

        return events

    def detect_revenge_trading(
        self, trades_df: pd.DataFrame, window_minutes: int = REVENGE_WINDOW_MINS
    ) -> list[RevengeTrade]:
        """
        Detect potential 'revenge trading' (tilt).
        Defined as trades occurring shortly after a loss.

        Args:
            trades_df: DataFrame of executed trades.
            window_minutes: Lookback window after a loss.

        Returns:
            List of RevengeTrade objects containing tilt details.
        """
        if trades_df.empty or len(trades_df) < 2:
            return []

        df = trades_df.sort_values("created_at").copy()
        # Ensure UTC
        if df["created_at"].dt.tz is None:
            df["created_at"] = pd.to_datetime(df["created_at"]).dt.tz_localize(UTC)

        revenge_trades = []
        for i in range(1, len(df)):
            prev_trade = df.iloc[i - 1]
            curr_trade = df.iloc[i]

            time_diff = (curr_trade["created_at"] - prev_trade["created_at"]).total_seconds() / 60.0
            if prev_trade["pnl"] < 0 and 0 < time_diff <= window_minutes:
                # Check for lot size increase if available
                lot_increase = False
                if (
                    "lot_size" in curr_trade
                    and "lot_size" in prev_trade
                    and curr_trade["lot_size"] > prev_trade["lot_size"]
                ):
                    lot_increase = True

                revenge_trades.append(
                    RevengeTrade(
                        trade_id=int(curr_trade["id"]),
                        prev_trade_id=int(prev_trade["id"]),
                        time_diff_min=float(time_diff),
                        lot_increase=lot_increase,
                        pnl=float(curr_trade["pnl"]),
                    )
                )

        return revenge_trades

    def detect_drawdown_clusters(self, trades_df: pd.DataFrame) -> list[DrawdownCluster]:
        """Detect clusters of 3+ consecutive losing trades with equity impact analysis."""
        if trades_df.empty:
            return []

        # Ensure UTC-aware
        df = trades_df.copy()
        if df["created_at"].dt.tz is None:
            df["created_at"] = pd.to_datetime(df["created_at"]).dt.tz_localize(UTC)
        else:
            df["created_at"] = pd.to_datetime(df["created_at"]).dt.tz_convert(UTC)

        trades = df.sort_values("created_at").to_dict("records")

        clusters = []
        current_cluster = []

        def build_cluster(cluster_trades: list[dict[str, Any]]) -> DrawdownCluster:
            pnls = [t["pnl"] for t in cluster_trades]
            cumulative_pnl = np.cumsum(pnls)
            max_drop = float(np.min(cumulative_pnl)) if len(cumulative_pnl) > 0 else 0.0

            return DrawdownCluster(
                start_time=cluster_trades[0]["created_at"],
                end_time=cluster_trades[-1]["created_at"],
                trade_count=len(cluster_trades),
                total_loss=sum(pnls),
                max_equity_drop=abs(max_drop),
            )

        for trade in trades:
            if trade["pnl"] < 0:
                current_cluster.append(trade)
            elif len(current_cluster) >= 3:
                clusters.append(build_cluster(current_cluster))
                current_cluster = []
            else:
                current_cluster = []

        # Check last cluster
        if len(current_cluster) >= 3:
            clusters.append(build_cluster(current_cluster))

        return clusters

    def detect_profit_clusters(self, trades_df: pd.DataFrame) -> list[ProfitCluster]:
        """Detect clusters of 3+ consecutive winning trades."""
        if trades_df.empty:
            return []

        # Ensure UTC-aware
        df = trades_df.copy()
        if df["created_at"].dt.tz is None:
            df["created_at"] = pd.to_datetime(df["created_at"]).dt.tz_localize(UTC)
        else:
            df["created_at"] = pd.to_datetime(df["created_at"]).dt.tz_convert(UTC)

        trades = df.sort_values("created_at").to_dict("records")

        clusters = []
        current_cluster = []

        for trade in trades:
            if trade["pnl"] > 0:
                current_cluster.append(trade)
            elif len(current_cluster) >= 3:
                clusters.append(
                    ProfitCluster(
                        start_time=current_cluster[0]["created_at"],
                        end_time=current_cluster[-1]["created_at"],
                        trade_count=len(current_cluster),
                        total_profit=sum(t["pnl"] for t in current_cluster),
                    )
                )
                current_cluster = []
            else:
                current_cluster = []

        # Check last cluster
        if len(current_cluster) >= 3:
            clusters.append(
                ProfitCluster(
                    start_time=current_cluster[0]["created_at"],
                    end_time=current_cluster[-1]["created_at"],
                    trade_count=len(current_cluster),
                    total_profit=sum(t["pnl"] for t in current_cluster),
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

        # Multi-attribute: Algorithm + Volatility
        if "algorithm" in trades_df.columns and "volatility" in trades_df.columns:
            df = trades_df.copy()
            df["vol_bucket"] = df["volatility"].apply(self._extract_volatility_bucket)
            combos = df.groupby(["algorithm", "vol_bucket"])
            for (algo, vol), group in combos:
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
                        attribute="algo_volatility",
                        value=f"{algo} @ {vol} Vol",
                        win_rate=win_rate,
                        profit_factor=profit_factor,
                        total_trades=trade_count,
                    )
                )

        # Multi-attribute: Algorithm + Confidence
        if "algorithm" in trades_df.columns and "confidence" in trades_df.columns:
            df = trades_df.copy()
            df["conf_bucket"] = df["confidence"].apply(self._extract_confidence_bucket)
            combos = df.groupby(["algorithm", "conf_bucket"])
            for (algo, conf), group in combos:
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
                        attribute="algo_confidence",
                        value=f"{algo} @ {conf} Conf",
                        win_rate=win_rate,
                        profit_factor=profit_factor,
                        total_trades=trade_count,
                    )
                )

        # Session Overlaps (Enhancement)
        overlap_stats = self.analyze_session_overlaps(trades_df)
        results.extend(overlap_stats)

        return sorted(results, key=lambda x: x.profit_factor, reverse=True)

    def analyze_session_overlaps(self, trades_df: pd.DataFrame) -> list[PatternConcentration]:
        """
        Detect performance in session overlap periods (e.g. London/NY).

        Overlap periods often represent the highest liquidity and volatility,
        which can be both highly profitable and high risk for certain models.
        """
        if trades_df.empty:
            return []

        df = trades_df.copy()
        if "sessions" not in df.columns:
            df["sessions"] = df["created_at"].apply(self._get_session)

        df["overlap"] = df["sessions"].apply(
            lambda x: " / ".join(sorted(x)) if len(x) > 1 else None
        )

        results = []
        overlaps = df.dropna(subset=["overlap"])
        if overlaps.empty:
            return []

        for overlap in overlaps["overlap"].unique():
            group = overlaps[overlaps["overlap"] == overlap]
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
                    attribute="session_overlap",
                    value=str(overlap),
                    win_rate=win_rate,
                    profit_factor=profit_factor,
                    total_trades=trade_count,
                )
            )
        return results

    def analyze_blocked_motifs(
        self, signals_df: pd.DataFrame, blocked_df: pd.DataFrame
    ) -> list[SignalMotif]:
        """
        Identify recurring motifs in blocked signals.

        Helps identify if the system is rejecting profitable patterns (opportunity cost)
        or successfully filtering out toxic patterns.

        Args:
            signals_df: DataFrame of all model signals.
            blocked_df: DataFrame of blocked signal analysis (opportunity cost).

        Returns:
            Sorted list of motifs found in blocked signals.
        """
        if signals_df.empty or blocked_df.empty:
            return []

        # Join blocked info back to signals to get algo/vol/etc.
        # Assuming signal_id is the link
        if "signal_id" not in blocked_df.columns:
            return []

        df = signals_df.merge(blocked_df, left_on="id", right_on="signal_id")
        if df.empty:
            return []

        # Format DF for find_frequent_motifs expectations
        # Use would_have_won as proxy for 'win' and opportunity_cost_pnl for 'pnl'
        df["pnl"] = df["opportunity_cost_pnl"]
        # find_frequent_motifs expects a 'pnl' column and calculates 'win' from it
        # Actually find_frequent_motifs uses group['win'] = group['pnl'] > 0 if I recall
        # Let's re-read find_frequent_motifs logic.
        # It says: df["win"] = df["pnl"] > 0
        # Wait, I added df["win"] = df["pnl"] > 0 at the beginning of find_frequent_motifs

        return self.find_frequent_motifs(df)

    def analyze_rejection_quality(self, blocked_df: pd.DataFrame) -> list[RejectionQuality]:
        """Analyze the effectiveness of signal rejections based on opportunity cost."""
        if blocked_df.empty:
            return []

        results = []
        for reason in blocked_df["rejection_reason"].unique():
            if pd.isna(reason):
                continue
            group = blocked_df[blocked_df["rejection_reason"] == reason]
            total = len(group)
            # Correct block: signal would have lost (would_have_won=False)
            correct = len(group[~group["would_have_won"]])
            # Incorrect block: signal would have won (would_have_won=True)
            incorrect = len(group[group["would_have_won"]])
            accuracy = correct / total if total > 0 else 0.0
            opp_cost = group[group["would_have_won"]]["opportunity_cost_pnl"].sum()

            results.append(
                RejectionQuality(
                    reason=str(reason),
                    total_blocked=total,
                    correct_blocks=correct,
                    incorrect_blocks=incorrect,
                    accuracy=accuracy,
                    profit_opportunity_cost=float(opp_cost),
                )
            )
        return results

    def analyze_risk_blocks(
        self,
        risk_events_df: pd.DataFrame,
        signals_df: pd.DataFrame,
        trades_df: pd.DataFrame = None,
        blocked_df: pd.DataFrame = None,
        weak_state_window_hours: int = PRE_DRAWDOWN_WINDOW_HOURS,
    ) -> list[BlockReasonSummary]:
        """Summarize recurring risk block reasons with weak state correlation and efficiency."""
        if risk_events_df.empty:
            return []

        results = []
        counts = risk_events_df["event_type"].value_counts()

        # Calculate weak state correlation if trades are provided
        correlations = {}
        if trades_df is not None and not trades_df.empty:
            correlations = self.analyze_strategy_state_correlation(
                risk_events_df, trades_df, window_hours=weak_state_window_hours
            )

        # Rejection quality metrics
        rejection_metrics = {}
        if blocked_df is not None and not blocked_df.empty:
            qualities = self.analyze_rejection_quality(blocked_df)
            for q in qualities:
                rejection_metrics[q.reason] = (q.accuracy, q.profit_opportunity_cost)

        for reason, count in counts.items():
            # Find algorithms impacted by this reason if signal_id is present
            impacted_algos = []
            if (
                not signals_df.empty
                and "signal_id" in risk_events_df.columns
                and "algorithm" in signals_df.columns
            ):
                event_signals = risk_events_df[risk_events_df["event_type"] == reason]["signal_id"]
                relevant_signals = signals_df[signals_df["id"].isin(event_signals)]
                impacted_algos = list(relevant_signals["algorithm"].unique())

            metrics = rejection_metrics.get(reason, (0.0, 0.0))
            results.append(
                BlockReasonSummary(
                    reason=str(reason),
                    count=int(count),
                    impacted_algorithms=impacted_algos,
                    weak_state_correlation=correlations.get(reason, 0.0),
                    correct_rejection_rate=metrics[0],
                    profit_opportunity_cost=metrics[1],
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
        self,
        signals_df: pd.DataFrame,
        trades_df: pd.DataFrame,
        window_hours: int = PRE_DRAWDOWN_WINDOW_HOURS,
    ) -> list[SignalMotif]:
        """
        Identify signal motifs that frequently occur shortly before a drawdown cluster.

        These are 'early warning' motifs that might indicate a strategy is about to fail.
        A drawdown cluster is defined as 3+ consecutive losing trades.

        Args:
            signals_df: DataFrame containing all model signals.
            trades_df: DataFrame containing executed trades.
            window_hours: The look-back window in hours before a drawdown cluster starts.

        Returns:
            List of SignalMotif objects that appear in the pre-drawdown window.
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
            # Ensure sigs for comparison are UTC-aware
            sigs = signals_df.copy()
            if sigs["created_at"].dt.tz is None:
                sigs["created_at"] = sigs["created_at"].dt.tz_localize(UTC)

            mask = (sigs["created_at"] >= start_window) & (sigs["created_at"] < cluster.start_time)
            pre_cluster_signals.append(sigs[mask])

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
        Find recurring motifs in signals to identify robust performance clusters.

        Identifies high-probability winning (Golden) and losing (Toxic) signal combinations
        based on algorithm, direction, volatility, and session. If trades_df is provided,
        it also tracks motif presence within historical drawdown clusters.

        Args:
            signals_df: DataFrame containing model signals.
            trades_df: Optional DataFrame of executed trades to identify cluster overlap.

        Returns:
            Sorted list of SignalMotif objects, ordered by statistical significance.
        """
        if signals_df.empty or "volatility" not in signals_df.columns:
            return []

        # Ensure UTC-aware
        signals_df = signals_df.copy()
        if signals_df["created_at"].dt.tz is None:
            signals_df["created_at"] = pd.to_datetime(signals_df["created_at"]).dt.tz_localize(UTC)
        else:
            signals_df["created_at"] = pd.to_datetime(signals_df["created_at"]).dt.tz_convert(UTC)

        if trades_df is not None and not trades_df.empty:
            trades_df = trades_df.copy()
            if trades_df["created_at"].dt.tz is None:
                trades_df["created_at"] = pd.to_datetime(trades_df["created_at"]).dt.tz_localize(
                    UTC
                )
            else:
                trades_df["created_at"] = pd.to_datetime(trades_df["created_at"]).dt.tz_convert(UTC)

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
                # Ensure cluster times are UTC-aware Timestamps for comparison
                c_start = pd.Timestamp(cluster.start_time)
                if c_start.tzinfo is None:
                    c_start = c_start.replace(tzinfo=UTC)

                c_end = pd.Timestamp(cluster.end_time)
                if c_end.tzinfo is None:
                    c_end = c_end.replace(tzinfo=UTC)

                # Find trades in this cluster
                mask = (
                    (trades_df["created_at"] >= c_start)
                    & (trades_df["created_at"] <= c_end)
                    & (trades_df["pnl"] < 0)
                )
                cluster_trades = trades_df[mask]
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

            # Expectancy and Efficiency calculations
            pnls = group["pnl"].dropna()
            if not pnls.empty:
                avg_win = pnls[pnls > 0].mean() if (pnls > 0).any() else 0.0
                avg_loss = abs(pnls[pnls < 0].mean()) if (pnls < 0).any() else 0.0
                expectancy = (win_rate * avg_win) - ((1.0 - win_rate) * avg_loss)
                avg_pnl = pnls.mean()
                avg_abs_pnl = pnls.abs().mean()
                efficiency = avg_pnl / avg_abs_pnl if avg_abs_pnl > 0 else 0.0
            else:
                expectancy = 0.0
                efficiency = 0.0

            is_toxic = win_rate < 0.4 and expectancy < 0
            is_golden = win_rate > 0.6 and expectancy > 0

            results.append(
                SignalMotif(
                    algorithm=str(algo),
                    direction=int(direction),
                    volatility_bucket=str(vol),
                    confidence_bucket=str(conf),
                    session=str(sess),
                    frequency=int(freq),
                    win_rate=float(win_rate),
                    is_toxic=is_toxic,
                    is_golden=is_golden,
                    expectancy=float(expectancy),
                    efficiency_ratio=float(efficiency),
                    cluster_frequency=int(cluster_freq),
                )
            )

        # Score motifs by absolute impact (deviation from 0.5 win rate) * frequency
        def impact_score(m: SignalMotif) -> float:
            return float(abs(m.win_rate - 0.5) * np.log1p(m.frequency))

        return sorted(results, key=impact_score, reverse=True)

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
        self,
        risk_events_df: pd.DataFrame,
        trades_df: pd.DataFrame,
        window_hours: int = PRE_DRAWDOWN_WINDOW_HOURS,
    ) -> dict[str, float]:
        """
        Detect if risk blocks increase during 'weak strategy states'.

        Weak state is defined as the window preceding a drawdown cluster
        plus the duration of the drawdown cluster itself.

        Args:
            risk_events_df: DataFrame of risk management events (rejections).
            trades_df: DataFrame of executed trades.
            window_hours: Hours preceding a cluster to consider 'weak'.

        Returns:
            Dictionary mapping event type to the percentage of occurrences in weak states.
        """
        if risk_events_df.empty or trades_df.empty:
            return {}

        clusters = self.detect_drawdown_clusters(trades_df)
        if not clusters:
            return dict.fromkeys(risk_events_df["event_type"].unique(), 0.0)

        # Mark 'weak' time windows: window_hours before any drawdown cluster PLUS cluster period
        weak_windows = []
        for cluster in clusters:
            # Ensure cluster start/end are UTC
            c_start = cluster.start_time
            if c_start.tzinfo is None:
                c_start = c_start.replace(tzinfo=UTC)
            c_end = cluster.end_time
            if c_end.tzinfo is None:
                c_end = c_end.replace(tzinfo=UTC)

            start_time = c_start - pd.Timedelta(hours=window_hours)
            weak_windows.append((start_time, c_end))

        def is_weak(dt: datetime) -> bool:
            # Ensure dt is timezone-aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return any(start <= dt <= end for start, end in weak_windows)

        # Ensure risk_events_df created_at is available and formatted
        df = risk_events_df.copy()
        if "created_at" not in df.columns:
            return dict.fromkeys(df["event_type"].unique(), 0.0)

        df["is_weak_state"] = df["created_at"].apply(is_weak)

        results = {}
        for reason in df["event_type"].unique():
            group = df[df["event_type"] == reason]
            if len(group) == 0:
                results[reason] = 0.0
                continue
            weak_count = group["is_weak_state"].sum()
            results[reason] = float(weak_count / len(group))

        return results

    def find_combination_motifs(
        self, signals_df: pd.DataFrame, trades_df: pd.DataFrame, window_minutes: int = 60
    ) -> list[CombinationMotif]:
        """
        Detect recurring combinations of multiple signals within a short window.

        These motifs are identified by looking at signals from different algorithms
        occurring within a short window that frequently precede drawdown clusters
        (Toxic) or profit clusters (Golden).

        Args:
            signals_df: DataFrame of model signals.
            trades_df: DataFrame of executed trades.
            window_minutes: The look-back window in minutes before a cluster.

        Returns:
            List of CombinationMotif objects.
        """
        if signals_df.empty or trades_df.empty:
            return []

        # Ensure UTC-awareness for comparisons
        sigs = signals_df.copy()
        if sigs["created_at"].dt.tz is None:
            sigs["created_at"] = sigs["created_at"].dt.tz_localize(UTC)
        else:
            sigs["created_at"] = sigs["created_at"].dt.tz_convert(UTC)

        drawdown_clusters = self.detect_drawdown_clusters(trades_df)
        profit_clusters = self.detect_profit_clusters(trades_df)

        results = []

        # Process Toxic Combinations
        toxic_combos = self._find_combos_before_clusters(
            sigs, drawdown_clusters, window_minutes, is_toxic=True
        )
        results.extend(toxic_combos)

        # Process Golden Combinations
        golden_combos = self._find_combos_before_clusters(
            sigs, profit_clusters, window_minutes, is_toxic=False
        )
        results.extend(golden_combos)

        return sorted(results, key=lambda x: x.frequency, reverse=True)

    def _find_combos_before_clusters(
        self,
        sigs: pd.DataFrame,
        clusters: list[DrawdownCluster] | list[ProfitCluster],
        window_minutes: int,
        is_toxic: bool,
    ) -> list[CombinationMotif]:
        """Internal helper to find signal combinations preceding clusters."""
        if not clusters:
            return []

        combinations = []
        for cluster in clusters:
            cluster_start = cluster.start_time
            if cluster_start.tzinfo is None:
                cluster_start = cluster_start.replace(tzinfo=UTC)
            else:
                cluster_start = cluster_start.astimezone(UTC)

            start_window = cluster_start - pd.Timedelta(minutes=window_minutes)

            pre_cluster = sigs[
                (sigs["created_at"] >= start_window) & (sigs["created_at"] <= cluster_start)
            ]

            if len(pre_cluster) >= 2:
                pattern = sorted(
                    [f"{row['algorithm']}:{row['direction']}" for _, row in pre_cluster.iterrows()]
                )

                pre_cluster = pre_cluster.copy()
                pre_cluster["session"] = pre_cluster["created_at"].apply(
                    lambda x: (self._get_session(x) or ["Unknown"])[0]
                )
                pre_cluster["vol_bucket"] = pre_cluster["volatility"].apply(
                    self._extract_volatility_bucket
                )

                sessions = pre_cluster["session"].unique()
                dom_session = sessions[0] if len(sessions) == 1 else "Mixed"

                vol_buckets = pre_cluster["vol_bucket"].unique()
                dom_vol = vol_buckets[0] if len(vol_buckets) == 1 else "Mixed"

                combinations.append((tuple(pattern), dom_session, dom_vol))

        if not combinations:
            return []

        counts = Counter(combinations)
        results = []

        for (pattern_tuple, sess, vol), count in counts.items():
            if count >= 2:
                results.append(
                    CombinationMotif(
                        patterns=list(pattern_tuple),
                        frequency=count,
                        avg_pnl_after=0.0,
                        is_toxic=is_toxic,
                        is_golden=not is_toxic,
                        session=sess,
                        volatility_bucket=vol,
                    )
                )
        return results

    def analyze_performance_decay(
        self, trades_df: pd.DataFrame, window_size: int = DECAY_WINDOW_SIZE
    ) -> PerformanceDecay | None:
        """
        Detect rolling performance decay based on profit factor trends.

        Analyzes alpha degradation by comparing the Profit Factor of recent trades
        against a trailing baseline. Significant drops trigger a decay alert,
        suggesting the strategy may no longer be aligned with current market regimes.
        """
        if trades_df.empty or len(trades_df) < window_size * 2:
            return None

        df = trades_df.sort_values("created_at").copy()

        def calc_pf(data: pd.DataFrame) -> float:
            wins = data[data["pnl"] > 0]["pnl"].sum()
            losses = abs(data[data["pnl"] < 0]["pnl"].sum())
            return wins / losses if losses > 0 else (float("inf") if wins > 0 else 1.0)

        recent_trades = df.tail(window_size)
        baseline_trades = df.iloc[-(window_size * 2) : -window_size]

        recent_pf = calc_pf(recent_trades)
        baseline_pf = calc_pf(baseline_trades)

        # Calculate decay trend (percentage change in PF)
        if baseline_pf == float("inf"):
            pf_trend = -1.0 if recent_pf < float("inf") else 0.0
        elif baseline_pf > 0:
            pf_trend = (recent_pf - baseline_pf) / baseline_pf
        else:
            pf_trend = 1.0 if recent_pf > 0 else 0.0

        return PerformanceDecay(
            window_size=window_size,
            profit_factor_trend=float(pf_trend),
            is_decaying=pf_trend < self.PF_DECAY_THRESHOLD,
            recent_pf=float(recent_pf),
            baseline_pf=float(baseline_pf),
        )

    def run_mining(self, weak_state_window_hours: int = PRE_DRAWDOWN_WINDOW_HOURS) -> JournalReport:
        """Execute full mining suite and return typed report."""
        from src.core.trade_logger import BlockedSignalAnalysis

        with self.Session() as session:
            # Fetch data
            trades_raw = (
                session.execute(select(Trade).where(Trade.is_deleted.is_(False))).scalars().all()
            )
            signals_raw = (
                session.execute(select(ModelSignal).where(ModelSignal.is_deleted.is_(False)))
                .scalars()
                .all()
            )
            risk_raw = (
                session.execute(select(RiskEvent).where(RiskEvent.is_deleted.is_(False)))
                .scalars()
                .all()
            )
            blocked_raw = (
                session.execute(
                    select(BlockedSignalAnalysis).where(BlockedSignalAnalysis.is_deleted.is_(False))
                )
                .scalars()
                .all()
            )

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
                        "lot_size": t.lot_size,
                        "volatility": t.signal.volatility if t.signal else None,
                        "confidence": t.signal.confidence if t.signal else None,
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

            blocked_df = pd.DataFrame(
                [
                    {
                        "signal_id": b.signal_id,
                        "rejection_reason": b.rejection_reason,
                        "would_have_won": b.would_have_won,
                        "opportunity_cost_pnl": b.opportunity_cost_pnl,
                    }
                    for b in blocked_raw
                ]
            )

            # Ensure sessions are available for pattern concentration
            if not trades_df.empty:
                trades_df["sessions"] = trades_df["created_at"].apply(self._get_session)

            return JournalReport(
                session_analysis=self.get_session_stats(trades_df),
                volatility_patterns=self.analyze_volatility_patterns(signals_df),
                performance_decay=self.analyze_performance_decay(trades_df),
                drawdown_clusters=self.detect_drawdown_clusters(trades_df),
                profit_clusters=self.detect_profit_clusters(trades_df),
                profitable_concentrations=self.find_profitable_patterns(trades_df),
                risk_block_summary=self.analyze_risk_blocks(
                    risk_df,
                    signals_df,
                    trades_df,
                    blocked_df,
                    weak_state_window_hours=weak_state_window_hours,
                ),
                rejection_quality=self.analyze_rejection_quality(blocked_df),
                overconfidence_events=self.detect_overconfidence(trades_df),
                recurring_motifs=self.find_frequent_motifs(signals_df, trades_df),
                pre_drawdown_motifs=self.detect_pre_drawdown_motifs(signals_df, trades_df),
                combination_motifs=self.find_combination_motifs(signals_df, trades_df),
                revenge_trades=self.detect_revenge_trading(trades_df),
                blocked_motifs=self.analyze_blocked_motifs(signals_df, blocked_df),
                avg_win_duration=durations["avg_win_duration"],
                avg_loss_duration=durations["avg_loss_duration"],
            )
