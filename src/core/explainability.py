"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/explainability.py
Signal explainability and attribution engine.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from typing import Dict, List, Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

class AttributionItem(BaseModel):
    """Individual feature or cluster attribution."""
    name: str
    weight: float
    contribution: float  # weight * value or similar

class ModelAttribution(BaseModel):
    """Full model attribution breakdown."""
    clusters: List[AttributionItem]
    top_features: List[AttributionItem]

class SignalExplanation(BaseModel):
    """Structured trade signal attribution."""
    symbol: str
    direction: int
    attribution: ModelAttribution
    regime_context: str
    risk_validation: str
    summary: str

class SignalExplainer:
    """
    Provides structured trade signal attribution by aggregating model outputs,
    feature clusters, and market context.
    """

    def __init__(self) -> None:
        pass

    def explain(
        self,
        symbol: str,
        direction: int,
        confidence: float,
        regime_label: str,
        risk_passed: bool,
        per_algo_votes: Dict[str, float]
    ) -> SignalExplanation:
        """
        Generate a human-readable and machine-readable explanation for a signal.
        """
        # Feature cluster placeholders
        clusters = [
            AttributionItem(name="Trend", weight=0.4, contribution=0.35 if direction != 0 else 0.0),
            AttributionItem(name="Volatility", weight=0.3, contribution=0.2),
            AttributionItem(name="Momentum", weight=0.2, contribution=0.15),
            AttributionItem(name="Volume", weight=0.1, contribution=0.05),
        ]

        top_features = [
            AttributionItem(name="SMA_Slope", weight=0.25, contribution=0.22),
            AttributionItem(name="RSI", weight=0.15, contribution=-0.05),
            AttributionItem(name="ATR", weight=0.1, contribution=0.08),
        ]

        attribution = ModelAttribution(clusters=clusters, top_features=top_features)

        dir_str = "BUY" if direction == 1 else "SELL" if direction == -1 else "HOLD"
        risk_str = "PASSED" if risk_passed else "FAILED"

        summary = (
            f"Signal {dir_str} for {symbol} with {confidence:.2%} confidence. "
            f"Market is in {regime_label} regime. Risk validation {risk_str}. "
            f"Consensus from: {', '.join(per_algo_votes.keys())}."
        )

        return SignalExplanation(
            symbol=symbol,
            direction=direction,
            attribution=attribution,
            regime_context=regime_label,
            risk_validation=risk_str,
            summary=summary
        )
