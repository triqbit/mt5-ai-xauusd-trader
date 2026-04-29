"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/explainability.py
Explainability engine for signal attribution and institutional transparency.
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
    """Individual component contribution."""

    name: str
    value: float
    weight: float = 1.0
    impact: str  # e.g., "POSITIVE", "NEGATIVE", "NEUTRAL"


class FeatureAttribution(BaseModel):
    """Breakdown of feature cluster contributions."""

    trend: float = 0.0
    volatility: float = 0.0
    momentum: float = 0.0
    volume: float = 0.0
    sentiment: float = 0.0
    top_features: List[AttributionItem] = Field(default_factory=list)


class ModelAttribution(BaseModel):
    """Breakdown of ensemble model contributions."""

    primary_algo: str
    ensemble_weights: Dict[str, float]
    model_outputs: Dict[str, float]  # Algorithm name -> raw output/confidence
    consensus_score: float


class RegimeContext(BaseModel):
    """Market regime context at the time of signal."""

    regime: str
    volatility_state: str
    trend_strength: float
    is_favorable: bool


class RiskValidation(BaseModel):
    """Risk management filter results."""

    passed_all: bool
    filters_checked: List[str]
    rejection_reason: Optional[str] = None
    risk_reward_ratio: float
    confidence_threshold: float


class SignalExplanation(BaseModel):
    """Structured explanation for a trading signal."""

    signal_id: Optional[int] = None
    symbol: str
    direction: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    summary: str
    features: FeatureAttribution
    models: ModelAttribution
    regime: RegimeContext
    risk: RiskValidation

    metadata: Dict[str, str] = Field(default_factory=dict)


class SignalExplainer:
    """
    Generates institutional-grade explanations for trade signals.
    Translates raw model outputs and risk checks into structured narratives.
    """

    def explain(
        self,
        symbol: str,
        direction: int,
        confidence: float,
        model_outputs: Dict[str, float],
        weights: Dict[str, float],
        regime_data: Dict[str, Any],
        risk_results: Dict[str, Any],
        feature_importance: Optional[Dict[str, float]] = None,
    ) -> SignalExplanation:
        """
        Aggregates data into a comprehensive SignalExplanation.
        """

        # 1. Feature Attribution
        feature_attr = self._build_feature_attribution(feature_importance)

        # 2. Model Attribution
        model_attr = ModelAttribution(
            primary_algo=max(model_outputs, key=model_outputs.get) if model_outputs else "unknown",
            ensemble_weights=weights,
            model_outputs=model_outputs,
            consensus_score=confidence
        )

        # 3. Regime Context
        regime_ctx = RegimeContext(
            regime=regime_data.get("regime", "UNKNOWN"),
            volatility_state=regime_data.get("volatility", "NORMAL"),
            trend_strength=regime_data.get("trend_strength", 0.0),
            is_favorable=regime_data.get("is_favorable", True)
        )

        # 4. Risk Validation
        risk_val = RiskValidation(
            passed_all=risk_results.get("passed", True),
            filters_checked=risk_results.get("filters", []),
            rejection_reason=risk_results.get("reason"),
            risk_reward_ratio=risk_results.get("rr", 0.0),
            confidence_threshold=risk_results.get("threshold", 0.55)
        )

        # 5. Summary Generation
        summary = self._generate_summary(symbol, direction, confidence, regime_ctx, risk_val)

        return SignalExplanation(
            symbol=symbol,
            direction=direction,
            summary=summary,
            features=feature_attr,
            models=model_attr,
            regime=regime_ctx,
            risk=risk_val
        )

    def _build_feature_attribution(self, importance: Optional[Dict[str, float]]) -> FeatureAttribution:
        """Categorize feature importance into clusters."""
        if not importance:
            return FeatureAttribution()

        # Example categorization logic
        clusters = {"trend": 0.0, "volatility": 0.0, "momentum": 0.0, "volume": 0.0, "sentiment": 0.0}
        top_items = []

        for feat, val in importance.items():
            impact = "POSITIVE" if val > 0 else "NEGATIVE" if val < 0 else "NEUTRAL"
            top_items.append(AttributionItem(name=feat, value=val, impact=impact))

            feat_lower = feat.lower()
            if any(x in feat_lower for x in ["ema", "sma", "trend", "slope"]):
                clusters["trend"] += abs(val)
            elif any(x in feat_lower for x in ["atr", "std", "volat", "bb"]):
                clusters["volatility"] += abs(val)
            elif any(x in feat_lower for x in ["rsi", "macd", "momo", "roc"]):
                clusters["momentum"] += abs(val)
            elif any(x in feat_lower for x in ["vol", "obv", "vpvp"]):
                clusters["volume"] += abs(val)
            elif any(x in feat_lower for x in ["sent", "news", "twitter"]):
                clusters["sentiment"] += abs(val)

        return FeatureAttribution(
            trend=clusters["trend"],
            volatility=clusters["volatility"],
            momentum=clusters["momentum"],
            volume=clusters["volume"],
            sentiment=clusters["sentiment"],
            top_features=sorted(top_items, key=lambda x: abs(x.value), reverse=True)[:5]
        )

    def _generate_summary(
        self,
        symbol: str,
        direction: int,
        confidence: float,
        regime: RegimeContext,
        risk: RiskValidation
    ) -> str:
        """Create a human-readable narrative summary."""
        dir_str = "BUY" if direction > 0 else "SELL" if direction < 0 else "HOLD"

        if not risk.passed_all:
            return f"Signal {dir_str} for {symbol} REJECTED. Reason: {risk.rejection_reason}."

        summary = (
            f"Strong {dir_str} signal for {symbol} with {confidence:.1%} confidence. "
            f"Market is currently in a {regime.regime} regime with {regime.volatility_state} volatility. "
        )

        if regime.trend_strength > 0.7:
            summary += "High trend strength confirms entry alignment. "

        summary += f"Risk/Reward ratio of {risk.risk_reward_ratio:.2f} satisfies safety constraints."

        return summary


__all__ = [
    "AttributionItem",
    "FeatureAttribution",
    "ModelAttribution",
    "RegimeContext",
    "RiskValidation",
    "SignalExplanation",
    "SignalExplainer",
]
