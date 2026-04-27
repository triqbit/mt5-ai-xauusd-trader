"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/reporting.py
Research reporting engine for automated summary generation.
Author : Jules
License: MIT
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.core.trade_logger import TradeLogger
from src.research.templates import (
    ALLOCATION_REPORT_TEMPLATE,
    BENCHMARK_TEMPLATE,
    DRIFT_TEMPLATE,
    HYPERPARAMETER_TEMPLATE,
    PATTERN_REPORT_TEMPLATE,
    REGIME_REPORT_TEMPLATE,
    RESEARCH_SUMMARY_TEMPLATE,
    RISK_EVENT_TEMPLATE,
    STRESS_TEST_TEMPLATE,
)
from src.trading.risk_manager import RiskManager

logger = logging.getLogger(__name__)


class RegimeReport(BaseModel):
    """Market regime analysis report."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    current_regime: str
    confidence: float
    regime_characteristics: Dict[str, Any]
    transition_probability: Dict[str, float]


class StressTestReport(BaseModel):
    """Stress test outcomes report."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    scenario_name: str
    max_drawdown: float
    recovery_factor: float
    failure_points: List[str]
    resilience_score: float


class HyperparameterReport(BaseModel):
    """Hyperparameter robustness report."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    parameter_name: str
    sensitivity_score: float
    optimal_range: tuple[float, float]
    stability_metric: float


class PatternReport(BaseModel):
    """Trade pattern findings report."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    pattern_name: str
    frequency: int
    win_rate: float
    profit_factor: float
    average_holding_time_minutes: float


class DriftReport(BaseModel):
    """Model drift observations report."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_id: str
    feature_drift_score: float
    prediction_drift_score: float
    recalibration_recommended: bool
    affected_features: List[str]


class AllocationReport(BaseModel):
    """Allocation insights report."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: str
    current_weight: float
    target_weight: float
    risk_contribution: float
    leverage_used: float


class BenchmarkReport(BaseModel):
    """Benchmark comparisons report."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    benchmark_name: str
    alpha: float
    beta: float
    tracking_error: float
    information_ratio: float


class RiskEventReport(BaseModel):
    """Risk management events report."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str
    description: str
    symbol: Optional[str] = None


class ResearchSummary(BaseModel):
    """Aggregated research summary report."""
    report_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    regime_analysis: Optional[RegimeReport] = None
    stress_tests: List[StressTestReport] = Field(default_factory=list)
    hyperparameter_robustness: List[HyperparameterReport] = Field(default_factory=list)
    trade_patterns: List[PatternReport] = Field(default_factory=list)
    model_drift: List[DriftReport] = Field(default_factory=list)
    allocations: List[AllocationReport] = Field(default_factory=list)
    benchmarks: List[BenchmarkReport] = Field(default_factory=list)
    risk_events: List[RiskEventReport] = Field(default_factory=list)
    overall_sentiment: str = "Neutral"
    key_recommendations: List[str] = Field(default_factory=list)

    def to_json(self) -> str:
        """Export the report as a JSON string."""
        return self.model_dump_json(indent=4)

    def to_markdown(self) -> str:
        """Export the report as a Markdown string."""
        regime_md = "N/A"
        if self.regime_analysis:
            regime_md = REGIME_REPORT_TEMPLATE.substitute(
                current_regime=self.regime_analysis.current_regime,
                confidence_pct=round(self.regime_analysis.confidence * 100, 2),
                characteristics=json.dumps(self.regime_analysis.regime_characteristics),
                transitions=json.dumps(self.regime_analysis.transition_probability),
            )

        allocations_md = "\n".join(
            [
                ALLOCATION_REPORT_TEMPLATE.substitute(
                    symbol=a.symbol,
                    current_weight_pct=round(a.current_weight * 100, 2),
                    target_weight_pct=round(a.target_weight * 100, 2),
                    risk_contribution_pct=round(a.risk_contribution * 100, 2),
                    leverage_used=round(a.leverage_used, 2),
                )
                for a in self.allocations
            ]
        ) or "No allocation data available."

        patterns_md = "\n".join(
            [
                PATTERN_REPORT_TEMPLATE.substitute(
                    pattern_name=p.pattern_name,
                    frequency=p.frequency,
                    win_rate_pct=round(p.win_rate * 100, 2),
                    profit_factor=round(p.profit_factor, 2),
                    avg_holding_time=round(p.average_holding_time_minutes, 2),
                )
                for p in self.trade_patterns
            ]
        ) or "No trade pattern data available."

        stress_md = "\n".join(
            [
                STRESS_TEST_TEMPLATE.substitute(
                    scenario_name=s.scenario_name,
                    max_drawdown_pct=round(s.max_drawdown * 100, 2),
                    recovery_factor=round(s.recovery_factor, 2),
                    resilience_score=round(s.resilience_score, 2),
                    failure_points=", ".join(s.failure_points),
                )
                for s in self.stress_tests
            ]
        ) or "No stress test data available."

        hyper_md = "\n".join(
            [
                HYPERPARAMETER_TEMPLATE.substitute(
                    parameter_name=h.parameter_name,
                    sensitivity_score=round(h.sensitivity_score, 3),
                    optimal_range=str(h.optimal_range),
                    stability_metric=round(h.stability_metric, 3),
                )
                for h in self.hyperparameter_robustness
            ]
        ) or "No hyperparameter robustness data available."

        drift_md = "\n".join(
            [
                DRIFT_TEMPLATE.substitute(
                    model_id=d.model_id,
                    feature_drift_score=round(d.feature_drift_score, 3),
                    prediction_drift_score=round(d.prediction_drift_score, 3),
                    recalibration="Yes" if d.recalibration_recommended else "No",
                    affected_features=", ".join(d.affected_features),
                )
                for d in self.model_drift
            ]
        ) or "No model drift data available."

        benchmarks_md = "\n".join(
            [
                BENCHMARK_TEMPLATE.substitute(
                    benchmark_name=b.benchmark_name,
                    alpha=round(b.alpha, 4),
                    beta=round(b.beta, 4),
                    information_ratio=round(b.information_ratio, 4),
                    tracking_error=round(b.tracking_error, 4),
                )
                for b in self.benchmarks
            ]
        ) or "No benchmark data available."

        risk_events_md = "\n".join(
            [
                RISK_EVENT_TEMPLATE.substitute(
                    timestamp=r.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    event_type=r.event_type,
                    description=r.description,
                    symbol=r.symbol or "N/A",
                )
                for r in self.risk_events
            ]
        ) or "No risk events recorded."

        return RESEARCH_SUMMARY_TEMPLATE.substitute(
            report_id=self.report_id,
            timestamp=self.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
            overall_sentiment=self.overall_sentiment,
            key_recommendations="\n".join([f"- {r}" for r in self.key_recommendations]),
            regime_analysis=regime_md,
            allocations=allocations_md,
            trade_patterns=patterns_md,
            stress_tests=stress_md,
            hyperparameter_robustness=hyper_md,
            model_drift=drift_md,
            benchmarks=benchmarks_md,
            risk_audit=risk_events_md,
        )


class ResearchReporter:
    """
    Main entry point for generating research summaries.
    Aggregates data from various system components.
    """

    def __init__(
        self,
        trade_logger: Optional[TradeLogger] = None,
        risk_manager: Optional[RiskManager] = None,
    ) -> None:
        self.trade_logger = trade_logger
        self.risk_manager = risk_manager

    def generate_summary(self, report_id: str) -> ResearchSummary:
        """Generate a full research summary."""
        summary = ResearchSummary(
            report_id=report_id,
            trade_patterns=self._generate_trade_patterns(),
            allocations=self._generate_allocation_insights(),
            regime_analysis=self._generate_regime_analysis(),
            stress_tests=self._generate_stress_tests(),
            hyperparameter_robustness=self._generate_hyperparameter_robustness(),
            model_drift=self._generate_model_drift(),
            benchmarks=self._generate_benchmarks(),
            risk_events=self._generate_risk_audit(),
        )
        summary.key_recommendations = self._generate_recommendations(summary)
        return summary

    def _generate_trade_patterns(self) -> List[PatternReport]:
        """Generate trade pattern findings from TradeLogger."""
        if not self.trade_logger:
            return []

        # In a real system, this would query the DB for specific patterns
        # For now, we pull the general performance metrics as a proxy
        perf = self.trade_logger.read_performance_report()
        if perf.get("total_trades", 0) == 0:
            return []

        return [
            PatternReport(
                pattern_name="General Execution",
                frequency=perf.get("total_trades", 0),
                win_rate=perf.get("win_rate", 0.0),
                profit_factor=perf.get("profit_factor", 0.0),
                average_holding_time_minutes=30.0,  # Placeholder
            )
        ]

    def _generate_allocation_insights(self) -> List[AllocationReport]:
        """Generate allocation insights from RiskManager."""
        if not self.risk_manager:
            return []

        from src.trading.risk_manager import ALLOCATION_WEIGHTS

        reports = []
        for symbol, weight in ALLOCATION_WEIGHTS.items():
            reports.append(
                AllocationReport(
                    symbol=symbol,
                    current_weight=weight,
                    target_weight=weight,
                    risk_contribution=weight * 0.5,  # Simple proxy
                    leverage_used=1.0,
                )
            )
        return reports

    def _generate_regime_analysis(self) -> Optional[RegimeReport]:
        """Place holder for regime analysis."""
        return None

    def _generate_stress_tests(self) -> List[StressTestReport]:
        """Place holder for stress test outcomes."""
        return []

    def _generate_hyperparameter_robustness(self) -> List[HyperparameterReport]:
        """Place holder for hyperparameter robustness."""
        return []

    def _generate_model_drift(self) -> List[DriftReport]:
        """Place holder for model drift observations."""
        return []

    def _generate_benchmarks(self) -> List[BenchmarkReport]:
        """Place holder for benchmark comparisons."""
        return []

    def _generate_risk_audit(self) -> List[RiskEventReport]:
        """Retrieve recent risk events from TradeLogger."""
        if not self.trade_logger:
            return []

        events = self.trade_logger.get_risk_events(limit=50)
        return [
            RiskEventReport(
                timestamp=e.created_at,
                event_type=e.event_type,
                description=e.description,
                symbol=e.symbol,
            )
            for e in events
        ]

    def _generate_recommendations(self, summary: ResearchSummary) -> List[str]:
        """Generate recommendations based on the summary data."""
        return ["Maintain current strategy parameters."]
