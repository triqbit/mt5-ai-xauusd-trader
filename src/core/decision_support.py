"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/decision_support.py
Generates structured decision packets for institutional operator oversight.
Author : triqbit
License: MIT
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from src.core.explainability import SignalExplanation
from src.models.dynamic_ensemble import MarketRegime


class DecisionPacket(BaseModel):
    """
    Structured decision packet providing institutional operator confidence and oversight.
    Combines signal analytics, risk state, and explainability.
    """

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: str
    direction: int  # +1 buy, -1 sell, 0 hold
    confidence: float
    model_consensus: Dict[str, float]
    market_regime: MarketRegime
    risk_state: str  # e.g., "STABLE", "WARNING", "CRITICAL"
    is_blocked: bool
    block_reasons: List[str] = Field(default_factory=list)
    performance_context: Dict[str, float]
    explanation: Optional[SignalExplanation] = None

    def to_human_readable(self) -> str:
        """
        Generate an enterprise-safe human-readable summary of the decision.
        Optimized for terminal output and log files.
        """
        direction_str = "BUY" if self.direction > 0 else "SELL" if self.direction < 0 else "HOLD"
        status = "❌ REJECTED" if self.is_blocked else "✅ APPROVED"

        header = f" INSTITUTIONAL DECISION PACKET | {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC "
        lines = [
            "╔══════════════════════════════════════════════════════════════════════════╗",
            f"║{header:^74}║",
            "╠══════════════════════════════════════════════════════════════════════════╣",
            f"║ STATUS      : {status:58} ║",
            f"║ SYMBOL      : {self.symbol:58} ║",
            f"║ DIRECTION   : {direction_str:58} ║",
            f"║ CONFIDENCE  : {self.confidence * 100:>5.1f}%                                             ║",
            f"║ REGIME      : {self.market_regime.value:58} ║",
            f"║ RISK STATE  : {self.risk_state:58} ║",
            "╟──────────────────────────────────────────────────────────────────────────╢",
            "║ MODEL CONSENSUS:                                                         ║",
        ]

        for model, prob in self.model_consensus.items():
            lines.append(f"║  - {model:15}: {prob * 100:>5.1f}%                                        ║")

        if self.block_reasons:
            lines.append("╟──────────────────────────────────────────────────────────────────────────╢")
            lines.append("║ REJECTION REASONS:                                                       ║")
            for reason in self.block_reasons:
                lines.append(f"║  - {reason:69} ║")

        lines.append("╟──────────────────────────────────────────────────────────────────────────╢")
        lines.append("║ PERFORMANCE CONTEXT:                                                     ║")
        for metric, value in self.performance_context.items():
            lines.append(f"║  - {metric:15}: {value:>10.4f}                                       ║")

        if self.explanation:
            lines.append("╟──────────────────────────────────────────────────────────────────────────╢")
            lines.append("║ EXPLAINABILITY SUMMARY:                                                  ║")
            wrapped_summary = self.explanation.summary[:71]
            lines.append(f"║  {wrapped_summary:72}║")

        lines.append("╚══════════════════════════════════════════════════════════════════════════╝")
        return "\n".join(lines)


class DecisionSupport:
    """
    Orchestration layer for decision augmentation.
    Aggregates intelligence from models, risk, and regime detection.
    """

    def generate_packet(
        self,
        symbol: str,
        direction: int,
        confidence: float,
        model_consensus: Dict[str, float],
        market_regime: MarketRegime,
        risk_state: str,
        is_blocked: bool,
        block_reasons: List[str],
        performance_context: Dict[str, float],
        explanation: Optional[SignalExplanation] = None,
    ) -> DecisionPacket:
        """
        Synthesize all available data into a structured DecisionPacket.
        """
        return DecisionPacket(
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            model_consensus=model_consensus,
            market_regime=market_regime,
            risk_state=risk_state,
            is_blocked=is_blocked,
            block_reasons=block_reasons,
            performance_context=performance_context,
            explanation=explanation,
        )
