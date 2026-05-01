"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/explainability.py
Trade signal explainability and attribution system.
Provides structured breakdowns of why a signal was generated or rejected.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SignalDirection(int, Enum):
    """Trading signal direction."""

    BUY = 1
    SELL = -1
    HOLD = 0


class FeatureContribution(BaseModel):
    """Contribution from a specific feature cluster (e.g., Trend, Volatility, Liquidity)."""

    cluster_name: str = Field(..., description="Name of the feature cluster")
    contribution_score: float = Field(
        ..., description="Normalized contribution score (-1.0 to 1.0)"
    )
    impact_level: str = Field(..., description="Qualitative impact (Low, Medium, High)")
    summary: str = Field(..., description="Human-readable description of the contribution")


class ModelAttribution(BaseModel):
    """Breakdown of contributions from individual models within an ensemble."""

    model_name: str = Field(..., description="Name of the model (e.g., PPO, LSTM)")
    vote: SignalDirection = Field(..., description="The direction voted by this model")
    confidence: float = Field(..., description="Model's internal confidence score")
    weight: float = Field(..., description="Weight of this model in the ensemble")
    is_dominant: bool = Field(False, description="Whether this model drove the final decision")


class RiskAssessment(BaseModel):
    """Summary of risk management constraints and filters applied to the signal."""

    passed: bool = Field(..., description="Whether the signal passed all risk filters")
    rejection_reasons: List[str] = Field(
        default_factory=list, description="Reasons for rejection if any"
    )
    risk_reward_ratio: float = Field(..., description="Calculated R:R for the trade")
    drawdown_impact_pct: float = Field(..., description="Estimated impact on total drawdown")
    kelly_fraction: float = Field(0.0, description="Kelly Criterion suggested sizing")
    summary: str = Field(..., description="Human-readable risk assessment summary")


class RegimeContext(BaseModel):
    """Market regime context at the time of signal generation."""

    regime_name: str = Field(..., description="Detected market regime (e.g., Trending, Ranging)")
    confidence: float = Field(..., description="Regime detection confidence")
    volatility_state: str = Field(
        ..., description="Current volatility level (Low, Normal, High, Extreme)"
    )
    is_favorable: bool = Field(..., description="Whether the regime is favorable for the strategy")
    summary: str = Field(..., description="Contextual summary of the market state")


class SignalExplanation(BaseModel):
    """
    Root explanation object for a trade signal.
    Aggregates model, feature, risk, and regime data into a structured format.
    """

    signal_id: Optional[int] = Field(None, description="Database ID of the signal")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Time the explanation was generated",
    )
    symbol: str = Field(..., description="Trading symbol (e.g., XAUUSD)")
    direction: SignalDirection = Field(..., description="Final ensemble signal direction")
    total_confidence: float = Field(..., description="Aggregated ensemble confidence score")

    # Components
    model_attributions: List[ModelAttribution] = Field(..., description="Breakdown per model")
    feature_contributions: List[FeatureContribution] = Field(
        ..., description="Breakdown per feature cluster"
    )
    risk_assessment: RiskAssessment = Field(..., description="Risk management breakdown")
    regime_context: RegimeContext = Field(..., description="Market context breakdown")

    # Summaries
    human_readable_summary: str = Field(
        ..., description="Natural language explanation for operators"
    )
    machine_attribution: Dict[str, float] = Field(
        ..., description="Key-value pairs for automated post-trade analysis"
    )

    model_config = {"use_enum_values": False}


class SignalExplainer:
    """
    Orchestrator for generating signal explanations.
    Collects data from various system components and builds a SignalExplanation.
    """

    def __init__(self) -> None:
        pass

    def explain(
        self,
        symbol: str,
        direction: int,
        confidence: float,
        model_votes: Dict[str, Any],
        model_weights: Dict[str, float],
        risk_data: Dict[str, Any],
        regime_info: Dict[str, Any],
        feature_impacts: Optional[List[Dict[str, Any]]] = None,
    ) -> SignalExplanation:
        """
        Generate a comprehensive explanation for a trade signal.
        """
        # 1. Model Attribution
        attributions = []
        dominant_model = ""
        max_weighted_conf = -1.0

        for name, vote_idx in model_votes.items():
            # In ensemble.py: 0=buy, 1=sell, 2=hold.
            # Note: SignalDirection enum matches 1, -1, 0.
            # We need to map carefully.
            # EnsembleModel uses: direction_map = {0: 1, 1: -1, 2: 0}
            direction_map = {
                0: SignalDirection.BUY,
                1: SignalDirection.SELL,
                2: SignalDirection.HOLD,
            }
            vote_dir = direction_map.get(int(vote_idx), SignalDirection.HOLD)

            weight = model_weights.get(name, 0.0)
            # Simplified confidence for individual models if not provided
            model_conf = confidence if vote_dir.value == direction else 0.5

            weighted_conf = weight * model_conf
            if weighted_conf > max_weighted_conf:
                max_weighted_conf = weighted_conf
                dominant_model = name

            attributions.append(
                ModelAttribution(
                    model_name=name,
                    vote=vote_dir,
                    confidence=model_conf,
                    weight=weight,
                    is_dominant=False,  # Updated below
                )
            )

        for attr in attributions:
            if attr.model_name == dominant_model:
                attr.is_dominant = True

        # 2. Risk Assessment
        risk_assessment = RiskAssessment(
            passed=risk_data.get("passed", False),
            rejection_reasons=risk_data.get("rejection_reasons", []),
            risk_reward_ratio=risk_data.get("risk_reward", 0.0),
            drawdown_impact_pct=risk_data.get("drawdown_impact", 0.0),
            kelly_fraction=risk_data.get("kelly_fraction", 0.0),
            summary=risk_data.get("summary", "No risk data provided"),
        )

        # 3. Regime Context
        regime_context = RegimeContext(
            regime_name=regime_info.get("name", "Unknown"),
            confidence=regime_info.get("confidence", 0.0),
            volatility_state=regime_info.get("volatility", "Normal"),
            is_favorable=regime_info.get("is_favorable", True),
            summary=regime_info.get("summary", "Market state stable"),
        )

        # 4. Feature Contributions (Mocked if not provided)
        if not feature_impacts:
            feature_impacts = [
                {
                    "cluster": "Trend",
                    "score": 0.8,
                    "impact": "High",
                    "summary": "Strong bullish momentum detected",
                },
                {
                    "cluster": "Volatility",
                    "score": -0.2,
                    "impact": "Low",
                    "summary": "Volatility is slightly compressing",
                },
            ]

        contributions = [
            FeatureContribution(
                cluster_name=fi["cluster"],
                contribution_score=fi["score"],
                impact_level=fi["impact"],
                summary=fi["summary"],
            )
            for fi in feature_impacts
        ]

        # 5. Generate Human Readable Summary
        dir_str = "BUY" if direction == 1 else "SELL" if direction == -1 else "HOLD"
        reasoning = f"Ensemble generated a {dir_str} signal with {confidence:.1%} confidence. "
        reasoning += f"Primary driver was the {dominant_model} model. "
        reasoning += f"Market is currently in a {regime_context.regime_name} regime. "

        if risk_assessment.passed:
            reasoning += f"Signal passed all risk filters with R:R of {risk_assessment.risk_reward_ratio:.2f}."
        else:
            reasoning += (
                f"Signal REJECTED by risk filters: {', '.join(risk_assessment.rejection_reasons)}."
            )

        # 6. Machine Attribution
        machine_attr = {
            "model_confidence": confidence,
            "risk_score": 1.0 if risk_assessment.passed else 0.0,
            "regime_confluence": regime_context.confidence,
            "dominant_model_weight": model_weights.get(dominant_model, 0.0),
        }

        return SignalExplanation(
            symbol=symbol,
            direction=SignalDirection(direction),
            total_confidence=confidence,
            model_attributions=attributions,
            feature_contributions=contributions,
            risk_assessment=risk_assessment,
            regime_context=regime_context,
            human_readable_summary=reasoning,
            machine_attribution=machine_attr,
        )

    def format_for_terminal(self, explanation: SignalExplanation) -> str:
        """
        Format the explanation for terminal display.
        Uses 'rich' for pretty printing if available, otherwise returns plain text.
        """
        try:
            from rich import box
            from rich.console import Console
            from rich.panel import Panel
            from rich.table import Table

            console = Console(force_terminal=True)

            # 1. Main Header Panel
            status_color = (
                "green"
                if explanation.direction == SignalDirection.BUY
                else "red"
                if explanation.direction == SignalDirection.SELL
                else "yellow"
            )
            header = Panel(
                f"[bold {status_color}]{explanation.direction.name}[/bold {status_color}] for [bold]{explanation.symbol}[/bold]\n"
                f"Confidence: [bold]{explanation.total_confidence:.1%}[/bold]\n\n"
                f"{explanation.human_readable_summary}",
                title="Trade Signal Explanation",
                subtitle=f"ID: {explanation.signal_id or 'N/A'} | {explanation.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                box=box.DOUBLE,
            )

            # 2. Model Votes Table
            model_table = Table(title="Model Attribution", box=box.SIMPLE)
            model_table.add_column("Model", style="cyan")
            model_table.add_column("Vote", style="bold")
            model_table.add_column("Weight", justify="right")
            model_table.add_column("Confidence", justify="right")
            model_table.add_column("Dominant", justify="center")

            for attr in explanation.model_attributions:
                vote_color = (
                    "green"
                    if attr.vote == SignalDirection.BUY
                    else "red"
                    if attr.vote == SignalDirection.SELL
                    else "white"
                )
                model_table.add_row(
                    attr.model_name,
                    f"[{vote_color}]{attr.vote.name}[/{vote_color}]",
                    f"{attr.weight:.1%}",
                    f"{attr.confidence:.1%}",
                    "⭐" if attr.is_dominant else "",
                )

            # 3. Risk and Regime
            risk_status = (
                "[bold green]PASSED[/bold green]"
                if explanation.risk_assessment.passed
                else "[bold red]FAILED[/bold red]"
            )
            risk_info = (
                f"Risk Gate: {risk_status}\n"
                f"R:R Ratio: [bold]{explanation.risk_assessment.risk_reward_ratio:.2f}[/bold]\n"
                f"Kelly Size: [bold]{explanation.risk_assessment.kelly_fraction:.2%}[/bold]\n"
            )
            if explanation.risk_assessment.rejection_reasons:
                risk_info += f"Reasons: [dim]{', '.join(explanation.risk_assessment.rejection_reasons)}[/dim]"

            regime_info = (
                f"Market Regime: [bold cyan]{explanation.regime_context.regime_name}[/bold cyan]\n"
                f"Volatility: [bold]{explanation.regime_context.volatility_state}[/bold]\n"
                f"Favored: {'[green]YES[/green]' if explanation.regime_context.is_favorable else '[red]NO[/red]'}"
            )

            # Capture output
            with console.capture() as capture:
                console.print(header)
                console.print(model_table)
                console.print(Panel(risk_info, title="Risk Assessment"))
                console.print(Panel(regime_info, title="Market Context"))

            return capture.get()

        except ImportError:
            # Fallback to plain text
            output = "=== TRADE SIGNAL EXPLANATION ===\n"
            output += f"Symbol: {explanation.symbol} | Direction: {explanation.direction.name} | Conf: {explanation.total_confidence:.1%}\n"
            output += f"Summary: {explanation.human_readable_summary}\n\n"
            output += "Model Votes:\n"
            for attr in explanation.model_attributions:
                output += f"  - {attr.model_name}: {attr.vote.name} (W={attr.weight:.1%}, C={attr.confidence:.1%}) {'[DOMINANT]' if attr.is_dominant else ''}\n"
            output += f"\nRisk Assessment: {'PASSED' if explanation.risk_assessment.passed else 'FAILED'}\n"
            output += f"Regime: {explanation.regime_context.regime_name} ({explanation.regime_context.volatility_state})\n"
            return output
