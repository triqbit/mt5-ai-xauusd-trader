"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/decision_support.py
Generates a structured operator-facing decision packet before execution or review.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from pydantic import BaseModel, Field

from src.models.regime_detector import MarketRegime
from src.core.explainability import SignalExplanation

logger = logging.getLogger(__name__)

class SignalSummary(BaseModel):
    """Summary of the generated signal."""
    symbol: str
    direction: int
    direction_label: str
    confidence: float
    price: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ConsensusSummary(BaseModel):
    """Breakdown of model consensus."""
    weights: Dict[str, float]
    votes: Dict[str, float]
    agreement_score: float

class RiskState(BaseModel):
    """Risk management status."""
    passed: bool
    rejection_reason: Optional[str] = None
    lot_size: float
    risk_reward: float
    equity_drawdown: float

class PerformanceContext(BaseModel):
    """Recent performance context for the symbol/strategy."""
    recent_win_rate: float
    profit_factor: float
    consecutive_losses: int

class DecisionPacket(BaseModel):
    """
    Consolidated decision packet for operator review.
    Provides institutional confidence through decision augmentation.
    """
    signal: SignalSummary
    consensus: ConsensusSummary
    regime: MarketRegime
    risk: RiskState
    performance: PerformanceContext
    explainability: SignalExplanation
    human_summary: str

class DecisionSupport:
    """
    Orchestrates the creation of a DecisionPacket by aggregating data
    from models, risk managers, and market context.
    """

    def __init__(self) -> None:
        pass

    def generate_packet(
        self,
        symbol: str,
        direction: int,
        confidence: float,
        price: float,
        per_algo_votes: Dict[str, float],
        model_weights: Dict[str, float],
        regime: MarketRegime,
        risk_passed: bool,
        rejection_reason: Optional[str],
        lot_size: float,
        risk_reward: float,
        equity_drawdown: float,
        recent_stats: Dict[str, Any],
        explanation: SignalExplanation
    ) -> DecisionPacket:
        """
        Assemble the full DecisionPacket.
        """
        direction_label = "BUY" if direction == 1 else "SELL" if direction == -1 else "HOLD"

        signal_sum = SignalSummary(
            symbol=symbol,
            direction=direction,
            direction_label=direction_label,
            confidence=confidence,
            price=price
        )

        # Calculate agreement (simple heuristic)
        vote_values = list(per_algo_votes.values())
        agreement = 1.0 if len(set(vote_values)) == 1 else 0.5 # placeholder

        consensus = ConsensusSummary(
            weights=model_weights,
            votes=per_algo_votes,
            agreement_score=agreement
        )

        risk_state = RiskState(
            passed=risk_passed,
            rejection_reason=rejection_reason,
            lot_size=lot_size,
            risk_reward=risk_reward,
            equity_drawdown=equity_drawdown
        )

        perf_context = PerformanceContext(
            recent_win_rate=recent_stats.get("win_rate", 0.0),
            profit_factor=recent_stats.get("profit_factor", 0.0),
            consecutive_losses=recent_stats.get("consecutive_losses", 0)
        )

        human_summary = (
            f"Decision: {direction_label} {symbol} @ {price:.2f}. "
            f"Confidence: {confidence:.2%}. Regime: {regime.label}. "
            f"Risk: {'APPROVED' if risk_passed else 'REJECTED'}. "
            f"Summary: {explanation.summary}"
        )

        return DecisionPacket(
            signal=signal_sum,
            consensus=consensus,
            regime=regime,
            risk=risk_state,
            performance=perf_context,
            explainability=explanation,
            human_summary=human_summary
        )
