"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/explainability.py
Post-signal attribution and explainability engine.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AttributionItem(BaseModel):
    """Individual feature or cluster contribution to a model's decision."""

    name: str
    contribution: float = Field(..., description="-1.0 to 1.0 (sell vs buy bias)")
    weight: float = Field(..., description="0.0 to 1.0 (relative importance)")
    cluster: str = Field(default="Other", description="Category: Trend, Volatility, Momentum, etc.")


class ModelAttribution(BaseModel):
    """Detailed breakdown of a specific model's decision within the ensemble."""

    algorithm: str
    confidence: float
    contributions: List[AttributionItem] = Field(default_factory=list)


class ExecutionFilterSummary(BaseModel):
    """Status of a specific risk or execution filter layer."""

    filter_name: str
    passed: bool
    reason: Optional[str] = None


class MarketContext(BaseModel):
    """Current market regime and environmental state."""

    regime: str = "Unknown"
    volatility: str = "Normal"
    trend_strength: float = 0.0
    additional_info: Dict[str, Any] = Field(default_factory=dict)


class SignalExplanation(BaseModel):
    """
    Structured, institution-grade explanation of a trade signal.
    Combines model attribution, risk constraints, and market context.
    """

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: str
    direction: int  # +1 Buy, -1 Sell, 0 Hold
    overall_confidence: float
    summary: str
    models: List[ModelAttribution] = Field(default_factory=list)
    execution_filters: List[ExecutionFilterSummary] = Field(default_factory=list)
    market_context: MarketContext
    risk_constraints: List[ExecutionFilterSummary] = Field(
        default_factory=list, description="Detailed breakdown of risk management layers"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Return machine-readable representation."""
        return self.model_dump()


class SignalExplainer:
    """
    Orchestrates the generation of signal explanations by aggregating
    data from models, risk manager, and market state.
    """

    def __init__(self) -> None:
        pass

    def explain(
        self,
        symbol: str,
        direction: int,
        confidence: float,
        model_outputs: Dict[str, Dict[str, Any]],
        risk_reasons: List[str],
        market_data: Optional[Dict[str, Any]] = None,
        feature_importance: Optional[Dict[str, float]] = None,
    ) -> SignalExplanation:
        """
        Produce a comprehensive SignalExplanation object.
        """
        # 1. Build Model Attributions
        models = []
        for algo, output in model_outputs.items():
            contributions = []
            if feature_importance:
                for feat, imp in feature_importance.items():
                    cluster = self._map_to_cluster(feat)
                    contributions.append(
                        AttributionItem(
                            name=feat,
                            contribution=direction * imp,  # Simplified sign attribution
                            weight=abs(imp),
                            cluster=cluster,
                        )
                    )

            models.append(
                ModelAttribution(
                    algorithm=algo,
                    confidence=output.get("confidence", 0.0),
                    contributions=contributions,
                )
            )

        # 2. Map Risk & Execution Filters
        # Common filters in the system
        filter_names = [
            "Circuit Breaker",
            "Daily Loss",
            "Max Positions",
            "Symbol Allocation",
            "Min Confidence",
            "Risk-Reward",
        ]
        filters = []
        for f_name in filter_names:
            reason = next(
                (r for r in risk_reasons if f_name.lower() in r.lower()), None
            )
            filters.append(
                ExecutionFilterSummary(
                    filter_name=f_name, passed=reason is None, reason=reason
                )
            )

        # 3. Market Context
        context = MarketContext()
        if market_data:
            context.regime = market_data.get("regime", "Unknown")
            context.volatility = market_data.get("volatility", "Normal")
            context.trend_strength = market_data.get("trend_strength", 0.0)
            context.additional_info = market_data.get("additional_info", {})

        # 4. Human-Readable Summary
        dir_name = {1: "BUY", -1: "SELL", 0: "HOLD"}.get(direction, "UNKNOWN")
        passed_risk = len(risk_reasons) == 0
        summary = (
            f"Signal {dir_name} generated for {symbol} with {confidence:.1%} confidence. "
        )

        if passed_risk:
            summary += "All execution filters PASSED. "
        else:
            summary += f"REJECTED by filters: {', '.join(risk_reasons)}. "

        summary += f"Market is currently in '{context.regime}' regime."

        return SignalExplanation(
            symbol=symbol,
            direction=direction,
            overall_confidence=confidence,
            summary=summary,
            models=models,
            execution_filters=filters,
            market_context=context,
            risk_constraints=filters,
        )

    def _map_to_cluster(self, feature_name: str) -> str:
        """Map technical feature names to human-readable clusters."""
        fn = feature_name.lower()
        if any(x in fn for x in ["rsi", "macd", "momentum", "roc"]):
            return "Momentum"
        if any(x in fn for x in ["atr", "std", "volat", "bb"]):
            return "Volatility"
        if any(x in fn for x in ["sma", "ema", "trend", "slope"]):
            return "Trend"
        if any(x in fn for x in ["vol", "obv", "mfi"]):
            return "Volume"
        return "Price Action"


__all__ = [
    "AttributionItem",
    "ExecutionFilterSummary",
    "MarketContext",
    "ModelAttribution",
    "SignalExplainer",
    "SignalExplanation",
]
