"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/explainability.py
Trade explanation engine providing structured interpretability for model signals.
Breaks down contributions from filters, models, features, regimes, and risk.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FilterContribution(BaseModel):
    """Contribution from an execution filter layer."""

    filter_name: str
    passed: bool
    value: Optional[float] = None
    threshold: Optional[float] = None
    message: str


class ModelContribution(BaseModel):
    """Contribution from an individual model in the ensemble."""

    model_name: str
    weight: float
    direction: int  # +1 buy, -1 sell, 0 hold
    confidence: float
    raw_probs: Dict[str, float] = Field(default_factory=dict)


class FeatureContribution(BaseModel):
    """Contribution from a group of features (e.g., Momentum, Volatility)."""

    group_name: str
    importance: float  # -1.0 to 1.0
    description: str


class RegimeContext(BaseModel):
    """Market regime context at the time of the trade."""

    regime: str
    confidence: float
    impact_multiplier: float = 1.0
    description: str


class RiskConstraint(BaseModel):
    """Risk management constraint status."""

    name: str
    limit: float
    actual: float
    status: str  # OK, WARNING, VIOLATED


class TradeExplanation(BaseModel):
    """
    Structured explanation for a trade signal.
    Suitable for logs, dashboards, and post-trade analysis.
    """

    symbol: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    direction: int
    confidence: float
    summary: str

    execution_filters: List[FilterContribution] = Field(default_factory=list)
    model_outputs: List[ModelContribution] = Field(default_factory=list)
    feature_clusters: List[FeatureContribution] = Field(default_factory=list)
    regime_context: Optional[RegimeContext] = None
    risk_constraints: List[RiskConstraint] = Field(default_factory=list)

    # Machine-readable attribution for quantitative analysis
    attribution: Dict[str, float] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert explanation to a dictionary for logging/API."""
        return self.model_dump()


class TradeExplainer:
    """
    Engine to generate TradeExplanation objects from system state.
    """

    def explain(
        self,
        symbol: str,
        direction: int,
        confidence: float,
        model_results: Optional[List[Dict[str, Any]]] = None,
        filter_results: Optional[List[Dict[str, Any]]] = None,
        regime: Optional[Dict[str, Any]] = None,
        risk_status: Optional[List[Dict[str, Any]]] = None,
        feature_importance: Optional[Dict[str, float]] = None,
    ) -> TradeExplanation:
        """
        Generate a comprehensive trade explanation.
        """
        # 1. Parse Model Contributions
        models = []
        if model_results:
            for m in model_results:
                models.append(ModelContribution(**m))

        # 2. Parse Execution Filters
        filters = []
        if filter_results:
            for f in filter_results:
                filters.append(FilterContribution(**f))

        # 3. Parse Regime Context
        regime_ctx = None
        if regime:
            regime_ctx = RegimeContext(**regime)

        # 4. Parse Risk Constraints
        risks = []
        if risk_status:
            for r in risk_status:
                risks.append(RiskConstraint(**r))

        # 5. Parse Feature Clusters (mocking grouping for now)
        features = []
        if feature_importance:
            for group, importance in feature_importance.items():
                features.append(
                    FeatureContribution(
                        group_name=group,
                        importance=importance,
                        description=f"Contribution from {group} indicators",
                    )
                )

        # 6. Generate Human-Readable Summary
        summary = self._generate_summary(direction, confidence, regime_ctx, filters, risks)

        return TradeExplanation(
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            summary=summary,
            execution_filters=filters,
            model_outputs=models,
            feature_clusters=features,
            regime_context=regime_ctx,
            risk_constraints=risks,
            attribution=feature_importance or {},
        )

    def _generate_summary(
        self,
        direction: int,
        confidence: float,
        regime: Optional[RegimeContext],
        filters: List[FilterContribution],
        risks: List[RiskConstraint],
    ) -> str:
        """Constructs a natural language summary of the trade decision."""
        dir_str = "BUY" if direction > 0 else "SELL" if direction < 0 else "HOLD"

        rejection_reasons = [f.message for f in filters if not f.passed]
        risk_violations = [r.name for r in risks if r.status == "VIOLATED"]

        if rejection_reasons or risk_violations:
            reason = rejection_reasons[0] if rejection_reasons else risk_violations[0]
            return f"REJECTED {dir_str} at {confidence:.1%} confidence due to: {reason}."

        regime_str = f" in {regime.regime} market" if regime else ""
        return (
            f"Strong {dir_str} signal ({confidence:.1%}){regime_str}. "
            f"All {len(filters)} execution filters passed with optimal risk profile."
        )


__all__ = [
    "TradeExplanation",
    "TradeExplainer",
    "FilterContribution",
    "ModelContribution",
    "FeatureContribution",
    "RegimeContext",
    "RiskConstraint",
]
