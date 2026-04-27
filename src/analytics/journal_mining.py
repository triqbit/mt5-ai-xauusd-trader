"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/analytics/journal_mining.py
Analyzes executed and rejected trades for hidden patterns and strategic insights.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.core.trade_logger import RiskEvent, Trade, TradeLogger

logger = logging.getLogger(__name__)

class SessionAnalysis(BaseModel):
    """Analysis of trading activity by hour of the day."""
    hour: int
    trade_count: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    is_overtrading_risk: bool = False

class VolatilityPattern(BaseModel):
    """Analysis of performance under different 'volatility' regimes (proxied by SL distance)."""
    regime_name: str
    trade_count: int
    false_positive_rate: float
    avg_pnl: float

class DrawdownCluster(BaseModel):
    """A sequence of losing trades and their characteristics."""
    start_time: datetime
    end_time: datetime
    trade_count: int
    total_loss: float
    dominant_algorithm: Optional[str] = None
    common_factors: List[str] = []

class RejectionAnalysis(BaseModel):
    """Summary of why trades were rejected by risk management."""
    reason: str
    count: int
    impacted_symbols: List[str]
    last_occurrence: datetime

class MiningReport(BaseModel):
    """Final analytical report containing all mined patterns."""
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_analysis: List[SessionAnalysis]
    volatility_patterns: List[VolatilityPattern]
    drawdown_clusters: List[DrawdownCluster]
    profitable_concentrations: List[Dict[str, Any]]
    rejection_summary: List[RejectionAnalysis]
    recommendations: List[str]

class JournalMiner:
    """
    Data mining engine for trade journals.
    Connects to the TradeLogger database to extract patterns.
    """

    def __init__(self, logger_db: TradeLogger):
        self.logger_db = logger_db

    def run_full_analysis(self) -> MiningReport:
        """Executes all mining tasks and returns a comprehensive report."""
        with self.logger_db.Session() as session:
            trades = session.query(Trade).filter(Trade.status == "CLOSED").all()
            rejections = (
                session.query(RiskEvent)
                .filter(RiskEvent.event_type == "SIGNAL_REJECTED")
                .all()
            )

            report = MiningReport(
                session_analysis=self.analyze_sessions(trades),
                volatility_patterns=self.analyze_volatility_patterns(trades),
                drawdown_clusters=self.analyze_drawdown_clusters(trades),
                profitable_concentrations=self.analyze_profitable_concentrations(trades),
                rejection_summary=self.analyze_rejections(rejections),
                recommendations=[],
            )
            report.recommendations = self._generate_recommendations(report)
            return report

    def analyze_sessions(self, trades: List[Trade]) -> List[SessionAnalysis]:
        """Detects overtrading or performance peaks by hour."""
        if not trades:
            return []

        hourly_stats: Dict[int, List[float]] = {}
        for trade in trades:
            if trade.signal:
                hour = trade.signal.timestamp.hour
                if hour not in hourly_stats:
                    hourly_stats[hour] = []
                hourly_stats[hour].append(trade.pnl)

        results = []
        total_trades = len(trades)
        avg_trades_per_hour = total_trades / 24 if total_trades > 0 else 0

        for hour, pnls in sorted(hourly_stats.items()):
            win_count = sum(1 for p in pnls if p > 0)
            trade_count = len(pnls)
            results.append(SessionAnalysis(
                hour=hour,
                trade_count=trade_count,
                win_rate=win_count / trade_count if trade_count > 0 else 0,
                total_pnl=sum(pnls),
                avg_pnl=sum(pnls) / trade_count if trade_count > 0 else 0,
                is_overtrading_risk=trade_count > (avg_trades_per_hour * 2) and sum(pnls) < 0
            ))
        return results

    def analyze_volatility_patterns(self, trades: List[Trade]) -> List[VolatilityPattern]:
        """
        Analyzes false positives under volatility conditions.
        Uses SL distance as a proxy for market volatility at entry.
        """
        if not trades:
            return []

        # Categorize by SL distance (proxy for volatility)
        low_vol = []
        med_vol = []
        high_vol = []

        for trade in trades:
            if trade.signal and trade.signal.stop_loss:
                risk = abs(trade.signal.entry_price - trade.signal.stop_loss)
                # Heuristic thresholds for Gold (XAUUSD)
                if risk < 2.0:
                    low_vol.append(trade)
                elif risk < 5.0:
                    med_vol.append(trade)
                else:
                    high_vol.append(trade)

        results = []
        for name, group in [("Low Vol", low_vol), ("Med Vol", med_vol), ("High Vol", high_vol)]:
            if not group:
                continue

            neg_pnl_count = sum(1 for t in group if t.pnl <= 0)
            results.append(VolatilityPattern(
                regime_name=name,
                trade_count=len(group),
                false_positive_rate=neg_pnl_count / len(group),
                avg_pnl=sum(t.pnl for t in group) / len(group)
            ))
        return results

    def analyze_drawdown_clusters(self, trades: List[Trade]) -> List[DrawdownCluster]:
        """Identifies sequences of losing trades."""
        if not trades:
            return []

        # Sort trades by signal timestamp
        sorted_trades = sorted([t for t in trades if t.signal], key=lambda x: x.signal.timestamp)

        clusters = []
        current_cluster: List[Trade] = []

        for trade in sorted_trades:
            if trade.pnl < 0:
                current_cluster.append(trade)
            else:
                if len(current_cluster) >= 3: # Define a cluster as 3+ consecutive losses
                    clusters.append(self._build_cluster(current_cluster))
                current_cluster = []

        if len(current_cluster) >= 3:
            clusters.append(self._build_cluster(current_cluster))

        return clusters

    def _build_cluster(self, trades: List[Trade]) -> DrawdownCluster:
        algs = [t.signal.algorithm for t in trades if t.signal and t.signal.algorithm]
        dominant = max(set(algs), key=algs.count) if algs else None

        return DrawdownCluster(
            start_time=trades[0].signal.timestamp,
            end_time=trades[-1].signal.timestamp,
            trade_count=len(trades),
            total_loss=sum(t.pnl for t in trades),
            dominant_algorithm=dominant,
            common_factors=["Consecutive Losses"]
        )

    def analyze_profitable_concentrations(self, trades: List[Trade]) -> List[Dict[str, Any]]:
        """Finds high-edge signal combinations or algorithms."""
        if not trades:
            return []

        # Group by algorithm
        alg_stats: Dict[str, List[float]] = {}
        for trade in trades:
            if trade.signal and trade.signal.algorithm:
                alg = trade.signal.algorithm
                if alg not in alg_stats:
                    alg_stats[alg] = []
                alg_stats[alg].append(trade.pnl)

        concentrations = []
        for alg, pnls in alg_stats.items():
            win_rate = sum(1 for p in pnls if p > 0) / len(pnls)
            if win_rate > 0.6: # High edge threshold
                concentrations.append({
                    "factor": "algorithm",
                    "value": alg,
                    "win_rate": win_rate,
                    "total_pnl": sum(pnls),
                    "count": len(pnls)
                })
        return concentrations

    def analyze_rejections(self, rejections: List[RiskEvent]) -> List[RejectionAnalysis]:
        """Analyzes risk rejections to find weak strategy states."""
        if not rejections:
            return []

        stats: Dict[str, Dict[str, Any]] = {}
        for rej in rejections:
            reason = rej.description or "Unknown"
            if reason not in stats:
                stats[reason] = {
                    "count": 0,
                    "symbols": set(),
                    "last_seen": rej.created_at
                }
            stats[reason]["count"] += 1
            if rej.symbol:
                stats[reason]["symbols"].add(rej.symbol)
            if rej.created_at > stats[reason]["last_seen"]:
                stats[reason]["last_seen"] = rej.created_at

        return [
            RejectionAnalysis(
                reason=r,
                count=d["count"],
                impacted_symbols=list(d["symbols"]),
                last_occurrence=d["last_seen"]
            ) for r, d in stats.items()
        ]

    def _generate_recommendations(self, report: MiningReport) -> List[str]:
        """Translates data patterns into actionable strategy changes."""
        recommendations = []

        for sess in report.session_analysis:
            if sess.is_overtrading_risk:
                recommendations.append(f"Reduce activity during hour {sess.hour}: high volume with negative yield suggests overtrading.")

        for vol in report.volatility_patterns:
            if vol.false_positive_rate > 0.7:
                recommendations.append(f"Avoid {vol.regime_name} conditions: false positive rate is {vol.false_positive_rate:.1%}.")

        if report.drawdown_clusters:
            recommendations.append(f"Detected {len(report.drawdown_clusters)} drawdown clusters. Consider implementing a 'cool-down' period after 3 consecutive losses.")

        for rej in report.rejection_summary:
            if rej.count > 10:
                recommendations.append(f"Strategy frequently hits '{rej.reason}'. Re-align entry signals with risk parameters.")

        return recommendations
