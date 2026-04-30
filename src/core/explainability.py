"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/explainability.py
System for explaining why a trade signal was produced or rejected.
Provides structured and human-readable attribution for institutional transparency.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelAttribution(BaseModel):
    """Contribution from a specific AI model in the ensemble."""
    algo_name: str
    contribution_weight: float
    direction_signal: int  # +1, -1, 0
    confidence: float
    raw_output: Optional[Dict[str, Any]] = None


class FilterResult(BaseModel):
    """Result of an execution filter or technical heuristic."""
    filter_name: str
    passed: bool
    value: float
    threshold: float
    message: str


class RegimeContext(BaseModel):
    """Market regime context at the time of signal generation."""
    regime_type: str
    confidence: float
    key_features: Dict[str, float] = Field(default_factory=dict)


class RiskConstraintInfo(BaseModel):
    """Snapshot of risk constraints applied to the signal."""
    account_balance: float
    risk_per_trade: float
    max_drawdown_limit: float
    current_drawdown: float
    is_circuit_breaker_active: bool


class FeatureClusterInfo(BaseModel):
    """Categorization of the current market state into historical clusters."""
    cluster_id: int
    description: str
    similarity_score: float


class SignalExplanation(BaseModel):
    """
    Structured explanation for a trade signal.
    Suitable for logs, dashboards, and post-trade analysis.
    """
    signal_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: str
    direction: int
    summary: str
    model_attributions: List[ModelAttribution] = Field(default_factory=list)
    filter_results: List[FilterResult] = Field(default_factory=list)
    regime: Optional[RegimeContext] = None
    risk_constraints: Optional[RiskConstraintInfo] = None
    feature_clusters: Optional[FeatureClusterInfo] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SignalExplainer:
    """
    Orchestrator for generating signal explanations.
    Combines outputs from models, filters, and market context.
    """

    def explain(
        self,
        symbol: str,
        direction: int,
        attributions: List[ModelAttribution],
        filters: List[FilterResult],
        regime: Optional[RegimeContext] = None,
        risk: Optional[RiskConstraintInfo] = None,
        clusters: Optional[FeatureClusterInfo] = None,
        signal_id: Optional[str] = None,
    ) -> SignalExplanation:
        """Aggregate all components into a structured explanation."""
        summary = self.generate_summary(direction, attributions, filters, regime)

        return SignalExplanation(
            signal_id=signal_id,
            symbol=symbol,
            direction=direction,
            summary=summary,
            model_attributions=attributions,
            filter_results=filters,
            regime=regime,
            risk_constraints=risk,
            feature_clusters=clusters,
        )

    def generate_summary(
        self,
        direction: int,
        attributions: List[ModelAttribution],
        filters: List[FilterResult],
        regime: Optional[RegimeContext] = None,
    ) -> str:
        """Create a human-readable summary of the signal logic."""
        dir_str = "BUY" if direction > 0 else "SELL" if direction < 0 else "HOLD"
        if direction == 0:
            return "No trading signal generated: Neutral state."

        # Model consensus
        strongest_model = max(attributions, key=lambda x: x.confidence) if attributions else None
        consensus_pct = sum(1 for a in attributions if a.direction_signal == direction) / (len(attributions) or 1) * 100

        summary_parts = [
            f"{dir_str} signal generated with {consensus_pct:.0f}% ensemble consensus.",
        ]

        if strongest_model:
            summary_parts.append(
                f"Primary driver: {strongest_model.algo_name} (conf={strongest_model.confidence:.2f})."
            )

        # Filters
        failed_filters = [f.filter_name for f in filters if not f.passed]
        if failed_filters:
            summary_parts.append(f"Caution: Failed filters: {', '.join(failed_filters)}.")
        else:
            summary_parts.append("All execution filters passed.")

        # Regime context
        if regime:
            summary_parts.append(
                f"Market is currently in a {regime.regime_type} regime (confidence={regime.confidence:.2f})."
            )

        return " ".join(summary_parts)
