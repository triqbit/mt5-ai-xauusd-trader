"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/explainability.py

Trade signal explainability and attribution system.
Provides institutional-grade structured breakdowns of why a signal was generated,
including ensemble voting, feature impacts, and execution filter results.

This module is the core of the system's "Glass Box" architecture, ensuring
that every automated decision is traceable, justifiable, and auditable.

All attribution models in this module are immutable (frozen) and enforce strict
validation to ensure technical trust and a reliable audit trail.

Usage:
    explainer = SignalExplainer()
    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.85,
        ...
    )
    # Use explainer.format_for_terminal(explanation) for visualization

Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from src.core.constants import ModelAction, SignalDirection

if TYPE_CHECKING:
    from src.models.regime_detector import RegimeInfo
    from src.trading.execution_filter import ExecutionDecision

logger = logging.getLogger(__name__)


class FeatureContribution(BaseModel):
    """
    Structured contribution from a specific feature cluster.
    Provides both quantitative (score) and qualitative (impact, summary) attribution.

    This model is immutable (frozen) and forbids extra fields to ensure
    consistent and auditable feature impact reporting.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    cluster_name: str = Field(
        ..., description="Name of the feature cluster (e.g., Trend, Volatility)"
    )
    contribution_score: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Normalized contribution score (-1.0 to 1.0).",
    )
    impact_level: str = Field(..., description="Qualitative impact (Low, Medium, High)")
    summary: str = Field(..., description="Human-readable description of the contribution")


class ModelAttribution(BaseModel):
    """
    Detailed breakdown of an individual model's contribution to the ensemble decision.
    Tracks alignment, confidence, and relative dominance within the group.

    This model is immutable (frozen) and forbids extra fields to maintain
    traceability of the ensemble's internal voting mechanics.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_name: str = Field(..., description="Name of the model (e.g., PPO, LSTM)")
    vote: SignalDirection = Field(..., description="The direction voted by this model")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Model's internal confidence score (0.0 to 1.0)."
    )
    weight: float = Field(
        ..., ge=0.0, le=1.0, description="Weight of this model in the ensemble (0.0 to 1.0)."
    )
    is_dominant: bool = Field(False, description="Whether this model drove the final decision")
    dominance_ratio: float = Field(
        0.0, ge=0.0, le=1.0, description="Relative influence of this model in the decision."
    )


class RiskAssessment(BaseModel):
    """
    Summary of institutional risk management constraints applied to the signal.
    Captures rejection reasons, R:R quality, and Kelly-based sizing suggestions.

    This model is immutable (frozen) and forbids extra fields to ensure
    risk assessments are not modified after generation.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    passed: bool = Field(..., description="Whether the signal passed all risk filters")
    rejection_reasons: list[str] = Field(
        default_factory=list, description="Reasons for rejection if any"
    )
    risk_reward_ratio: float = Field(0.0, description="Calculated R:R for the trade")
    drawdown_impact_pct: float = Field(0.0, description="Estimated impact on total drawdown")
    kelly_fraction: float = Field(0.0, description="Kelly Criterion suggested sizing")
    summary: str = Field(
        "No risk data provided", description="Human-readable risk assessment summary"
    )


class RegimeContext(BaseModel):
    """
    Institutional market regime context at the time of signal generation.
    Decomposes the macro state into regime labels, volatility levels, and strategy favorability.

    This model is immutable (frozen) and forbids extra fields to preserve
    the market state snapshot at the time of execution.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    regime_name: str = Field(
        "Unknown", description="Detected market regime (e.g., Trending, Ranging)"
    )
    confidence: float = Field(
        0.0, ge=0.0, le=1.0, description="Regime detection confidence (0.0 to 1.0)."
    )
    volatility_state: str = Field(
        "Normal", description="Current volatility level (Low, Normal, High, Extreme)"
    )
    is_favorable: bool = Field(True, description="Whether the regime is favorable for the strategy")
    regime_alignment_score: float = Field(
        0.0, ge=0.0, le=1.0, description="Quantitative strategy suitability for this regime."
    )
    session_alignment: float = Field(
        0.5, ge=0.0, le=1.0, description="Alignment with current trading session (0.0 to 1.0)."
    )
    volatility_alignment: float = Field(
        0.5, ge=0.0, le=1.0, description="Alignment with current volatility state (0.0 to 1.0)."
    )
    summary: str = Field(
        "Market state stable", description="Contextual summary of the market state"
    )


class FilterResult(BaseModel):
    """
    Institutional audit record for an individual execution filter.
    Captures the pass/fail status along with observed values and their respective thresholds.

    This model is immutable (frozen) and forbids extra fields for technical trust.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    filter_name: str = Field(..., description="Name of the filter (e.g., Spread, Momentum)")
    passed: bool = Field(..., description="Whether the filter passed")
    value: Any = Field(None, description="Actual value observed")
    threshold: Any = Field(None, description="Threshold value for the filter")
    message: str | None = Field(None, description="Details about the filter result")


class ExecutionSummary(BaseModel):
    """
    Unified summary of the institutional execution filter cascade.
    Aggregates results from multiple technical and operational gates before signal release.

    This model is immutable (frozen) and forbids extra fields to ensure
    execution filter results remain consistent across the pipeline.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    passed: bool = Field(..., description="Whether all execution filters passed")
    filters: list[FilterResult] = Field(default_factory=list, description="Detailed filter results")
    summary: str = Field(..., description="Human-readable execution summary")


class SignalExplanation(BaseModel):
    """
    Institutional-grade root explanation object for a trade signal.
    Aggregates execution, model, feature, risk, and regime data into a unified
    structure suitable for real-time dashboards, post-trade analysis, and regulatory auditing.

    This model is immutable (frozen) and forbids extra fields to ensure that once an
    explanation is generated, it cannot be altered by downstream components.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)

    signal_id: int | None = Field(None, description="Database ID of the signal")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Time the explanation was generated",
    )
    symbol: str = Field(..., description="Trading symbol (e.g., XAUUSD)")
    direction: SignalDirection = Field(..., description="Final ensemble signal direction")
    total_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Aggregated ensemble confidence score (0.0 to 1.0).",
    )

    # Components
    execution_summary: ExecutionSummary = Field(..., description="Execution-level filter breakdown")
    model_attributions: list[ModelAttribution] = Field(..., description="Breakdown per model")
    feature_contributions: list[FeatureContribution] = Field(
        ..., description="Breakdown per feature cluster"
    )
    risk_assessment: RiskAssessment = Field(..., description="Risk management breakdown")
    regime_context: RegimeContext = Field(..., description="Market context breakdown")

    # Summaries
    human_readable_summary: str = Field(
        ..., description="Natural language explanation for operators"
    )
    machine_attribution: dict[str, Any] = Field(
        ..., description="Key-value pairs for automated post-trade analysis"
    )

    def get_confluence_score(self) -> float:
        """
        Calculates a weighted confluence score (0.0 to 1.0) based on institutional metrics.
        Weighted logic: 40% Confidence, 30% Regime, 15% Session, 15% Volatility.
        """
        weights = {
            "confidence": 0.40,
            "regime": 0.30,
            "session": 0.15,
            "volatility": 0.15,
        }
        score = (
            self.total_confidence * weights["confidence"]
            + self.regime_context.regime_alignment_score * weights["regime"]
            + self.regime_context.session_alignment * weights["session"]
            + self.regime_context.volatility_alignment * weights["volatility"]
        )
        return float(score)


class SignalExplainer:
    """
    Institutional-grade orchestrator for generating trade signal explanations.
    Collects data from ensemble models, risk managers, execution filters, and
    regime detectors to produce a unified, auditable attribution object.
    """

    FEATURE_MAPPING = {
        "Momentum": [
            "rsi",
            "mfi",
            "cci",
            "mom",
            "macd",
            "stoch",
            "willr",
            "ultosc",
            "returns",
            "log_returns",
            "dist_ema",
            "dist_vwap",
            "efficiency_ratio",
            "z_score",
        ],
        "Volatility": [
            "atr",
            "bb_",
            "keltner",
            "range",
            "ht_dcperiod",
            "ht_phasor",
            "ht_sine",
            "body_size",
            "day_range",
            "vol_of_vol",
            "vol_clustering",
            "kurtosis",
            "skewness",
        ],
        "Trend": ["slope", "ema", "adx", "ht_"],
        "Volume": ["vol", "obv", "vwap", "vpt", "vp_", "rvol", "vol_sma_20", "volume_ratio"],
        "Patterns": ["pattern_"],
    }

    def __init__(self) -> None:
        pass

    def _get_direction_icon(self, direction: SignalDirection | int) -> str:
        """Utility to get directional icon for UX consistency."""
        if isinstance(direction, int):
            return "📈" if direction > 0 else "📉" if direction < 0 else "⏸️"
        return (
            "📈"
            if direction == SignalDirection.BUY
            else "📉"
            if direction == SignalDirection.SELL
            else "⏸️"
        )

    def _get_impact_marker(self, level: str) -> str:
        """Utility to get visual density markers for impact levels."""
        return "●●●" if level == "High" else "●●○" if level == "Medium" else "●○○"

    def explain(
        self,
        symbol: str,
        direction: int,
        confidence: float,
        model_votes: dict[str, Any],
        model_weights: dict[str, float],
        risk_data: dict[str, Any],
        regime_info: dict[str, Any] | RegimeInfo,
        execution_data: dict[str, Any] | ExecutionDecision | None = None,
        feature_impacts: list[dict[str, Any]] | dict[str, float] | None = None,
        model_confidences: dict[str, float] | None = None,
        signal_id: int | None = None,
        session_alignment: float = 0.5,
        volatility_alignment: float = 0.5,
    ) -> SignalExplanation:
        """
        Generate a comprehensive explanation for a trade signal.

        Args:
            symbol: Trading symbol (e.g., "XAUUSD").
            direction: Numerical signal direction (1=Buy, -1=Sell, 0=Hold).
            confidence: Aggregated ensemble confidence (0.0 to 1.0).
            model_votes: Dictionary mapping model names to their actions (ModelAction index).
            model_weights: Dictionary mapping model names to their ensemble weights.
            risk_data: Raw risk assessment data (passed, rejection_reasons, risk_reward, etc.).
            regime_info: Market regime data or RegimeInfo object.
            execution_data: Optional execution filter data or ExecutionDecision object.
            feature_impacts: Optional list of cluster impacts or dict of individual feature scores.
            model_confidences: Optional dictionary mapping model names to their individual confidence scores.
            signal_id: Optional database ID of the signal for traceability.
            session_alignment: Alignment override for the current trading session (0.0 to 1.0).
            volatility_alignment: Alignment override for the current volatility state (0.0 to 1.0).

        Returns:
            A structured SignalExplanation object.
        """
        # 0. Robustness: Validate core inputs and provide defaults
        if not symbol:
            logger.warning("Empty symbol provided to SignalExplainer. Falling back to XAUUSD.")
            symbol = "XAUUSD"

        model_votes = model_votes or {}
        model_weights = model_weights or {}
        risk_data = risk_data or {}

        # 1. Execution Summary
        if execution_data is None:
            execution_summary = ExecutionSummary(
                passed=True, filters=[], summary="Execution filters bypassed"
            )
        elif hasattr(execution_data, "trace"):  # ExecutionDecision dataclass or pydantic model
            filters = []
            # Extract blocked_by if available (handles both dataclass and model validator outcomes)
            blocked_by = getattr(execution_data, "blocked_by", None)
            # Default to False for institutional safety (fail-closed)
            is_approved = getattr(execution_data, "is_approved", False)

            for name, res in getattr(execution_data, "trace", {}).items():
                filters.append(
                    FilterResult(
                        filter_name=name,
                        passed=res.get("passed", False),
                        message=f"Blocked by {blocked_by}" if blocked_by == name.upper() else None,
                        value=res.get("value")
                        or res.get("ratio")
                        or res.get("rsi")
                        or res.get("slope"),
                        threshold=res.get("threshold")
                        or res.get("max_drawdown")
                        or res.get("drift_threshold"),
                    )
                )
            execution_summary = ExecutionSummary(
                passed=is_approved,
                filters=filters,
                summary=f"Blocked by {blocked_by}"
                if blocked_by
                else "Passed all execution filters",
            )
        elif isinstance(execution_data, dict):
            execution_filters = [
                FilterResult(
                    filter_name=f.get("name", "Unknown"),
                    passed=f.get("passed", False),
                    value=f.get("value"),
                    threshold=f.get("threshold"),
                    message=f.get("message"),
                )
                for f in execution_data.get("filters", [])
                if isinstance(f, dict)
            ]

            execution_summary = ExecutionSummary(
                passed=execution_data.get("passed", False),
                filters=execution_filters,
                summary=execution_data.get("summary", "No execution data"),
            )
        else:
            logger.error(
                f"Malformed execution_data of type {type(execution_data)}. Using defaults."
            )
            execution_summary = ExecutionSummary(
                passed=False,
                filters=[],
                summary="Malformed execution data detected",
            )

        # 2. Model Attribution
        dominant_models = []
        max_weighted_conf = -1.0
        model_confidences = model_confidences or {}

        # First pass: Calculate weighted confidences and identify dominance
        total_weighted_conf = 0.0
        temp_attributions = []

        for name, vote_idx in model_votes.items():
            try:
                vote_dir = ModelAction(int(vote_idx)).to_direction()
            except (ValueError, TypeError):
                logger.warning(
                    f"Invalid vote index '{vote_idx}' for model '{name}'. Falling back to HOLD."
                )
                vote_dir = SignalDirection.HOLD

            weight = model_weights.get(name, 0.0)
            model_conf = model_confidences.get(name)
            if model_conf is None:
                model_conf = confidence if vote_dir.value == direction else 0.5

            weighted_conf = weight * model_conf if vote_dir.value == direction else 0.0
            total_weighted_conf += weighted_conf

            if weighted_conf > max_weighted_conf:
                max_weighted_conf = weighted_conf
                dominant_models = [name]
            elif abs(weighted_conf - max_weighted_conf) < 1e-6 and max_weighted_conf > 0:
                dominant_models.append(name)

            temp_attributions.append(
                {
                    "model_name": name,
                    "vote": vote_dir,
                    "confidence": model_conf,
                    "weight": weight,
                    "weighted_conf": weighted_conf,
                }
            )

        # Second pass: Calculate dominance ratio and finalize attribution objects
        final_attributions = []
        for attr_dict in temp_attributions:
            dom_ratio = (
                attr_dict["weighted_conf"] / total_weighted_conf if total_weighted_conf > 0 else 0.0
            )
            final_attributions.append(
                ModelAttribution(
                    model_name=attr_dict["model_name"],
                    vote=attr_dict["vote"],
                    confidence=attr_dict["confidence"],
                    weight=attr_dict["weight"],
                    is_dominant=attr_dict["model_name"] in dominant_models,
                    dominance_ratio=dom_ratio,
                )
            )

        # 3. Risk Assessment
        risk_assessment = RiskAssessment(
            passed=risk_data.get("passed", False),
            rejection_reasons=risk_data.get("rejection_reasons", []),
            risk_reward_ratio=risk_data.get("risk_reward", 0.0),
            drawdown_impact_pct=risk_data.get("drawdown_impact", 0.0),
            kelly_fraction=risk_data.get("kelly_fraction", 0.0),
            summary=risk_data.get("summary", "No risk data provided"),
        )

        # 4. Regime Context
        if regime_info is None:
            logger.warning("No regime_info provided to SignalExplainer. Using defaults.")
            regime_context = RegimeContext(
                regime_name="Unknown",
                confidence=0.0,
                volatility_state="Normal",
                is_favorable=True,
                regime_alignment_score=0.5,
                session_alignment=session_alignment,
                volatility_alignment=volatility_alignment,
                summary="No market regime context available.",
            )
        elif hasattr(regime_info, "label"):  # RegimeInfo pydantic model
            alignment = regime_info.confidence if regime_info.confidence > 0.6 else 0.4
            s_align = getattr(regime_info, "session_alignment", session_alignment)
            v_align = getattr(regime_info, "volatility_alignment", volatility_alignment)

            regime_context = RegimeContext(
                regime_name=str(regime_info.label.value).title(),
                confidence=regime_info.confidence,
                volatility_state="High" if regime_info.volatility_index > 1.5 else "Normal",
                is_favorable=regime_info.confidence > 0.6,
                regime_alignment_score=alignment,
                session_alignment=s_align,
                volatility_alignment=v_align,
                summary=f"Market in {regime_info.label.value} state with {regime_info.confidence:.1%} confidence.",
            )
        elif isinstance(regime_info, dict):
            regime_context = RegimeContext(
                regime_name=regime_info.get("name", "Unknown"),
                confidence=regime_info.get("confidence", 0.0),
                volatility_state=regime_info.get("volatility", "Normal"),
                is_favorable=regime_info.get("is_favorable", True),
                regime_alignment_score=regime_info.get("alignment_score", 0.5),
                session_alignment=regime_info.get("session_alignment", session_alignment),
                volatility_alignment=regime_info.get("volatility_alignment", volatility_alignment),
                summary=regime_info.get("summary", "Market state stable"),
            )
        else:
            logger.error(f"Malformed regime_info of type {type(regime_info)}. Using defaults.")
            regime_context = RegimeContext(
                regime_name="Error",
                confidence=0.0,
                volatility_state="Normal",
                is_favorable=False,
                session_alignment=session_alignment,
                volatility_alignment=volatility_alignment,
                summary="Malformed regime context detected.",
            )

        # 5. Feature Contributions (with clustering logic)
        contributions = []
        if feature_impacts is None:
            contributions = []
        elif isinstance(feature_impacts, list):
            contributions = [
                FeatureContribution(
                    cluster_name=fi.get("cluster", "Unknown"),
                    contribution_score=fi.get("score", 0.0),
                    impact_level=fi.get("impact", "Low"),
                    summary=fi.get("summary", "No feature summary"),
                )
                for fi in feature_impacts
                if isinstance(fi, dict)
            ]
        elif isinstance(feature_impacts, dict):
            cluster_data: dict[str, list[tuple[str, float]]] = {k: [] for k in self.FEATURE_MAPPING}
            cluster_data["Other"] = []

            for feat, score in feature_impacts.items():
                found = False
                for cluster, keywords in self.FEATURE_MAPPING.items():
                    if any(kw in feat.lower() for kw in keywords):
                        cluster_data[cluster].append((feat, score))
                        found = True
                        break
                if not found:
                    cluster_data["Other"].append((feat, score))

            for cluster, items in cluster_data.items():
                if not items:
                    continue

                scores = [item[1] for item in items]
                avg_score = sum(scores) / len(scores)
                abs_avg = abs(avg_score)
                impact = "High" if abs_avg > 0.6 else "Medium" if abs_avg > 0.3 else "Low"

                # Identify top drivers by absolute contribution for institutional transparency
                sorted_items = sorted(items, key=lambda x: abs(x[1]), reverse=True)
                top_drivers = [f"{name} ({score:+.2f})" for name, score in sorted_items[:3]]
                summary = f"Aggregate impact from {len(items)} features. Top drivers: {', '.join(top_drivers)}"

                contributions.append(
                    FeatureContribution(
                        cluster_name=cluster,
                        contribution_score=avg_score,
                        impact_level=impact,
                        summary=summary,
                    )
                )

        # 6. Generate Human Readable Summary with Strategic Reasoning
        dir_str = SignalDirection(direction).name
        reasoning = f"Ensemble generated a {dir_str} signal with {confidence:.1%} confidence. "
        if dominant_models:
            reasoning += f"Primary driver(s): {', '.join(dominant_models)}. "

        regime_lower = regime_context.regime_name.lower()
        strategic_edge = ""
        if "trending" in regime_lower:
            strategic_edge = (
                "Trending regimes provide high-velocity environments for momentum models, "
                "favoring persistent directional strength."
            )
        elif "ranging" in regime_lower:
            strategic_edge = (
                "Mean-reversion setups are prioritized in ranging regimes, "
                "where price oscillates within established liquidity corridors."
            )
        elif "volatile_breakout" in regime_lower:
            strategic_edge = (
                "Breakout regimes signal high-momentum expansions; "
                "models prioritize volatility-adjusted entries with tight trailing protection."
            )
        elif "low_volatility_drift" in regime_lower:
            strategic_edge = (
                "Quiet drift regimes require high precision; models favor steady "
                "low-volatility trends with minimal slippage impact."
            )
        elif "news_shock" in regime_lower:
            strategic_edge = (
                "News shocks trigger extreme non-linear price dislocations; "
                "automated execution is typically restricted to preserve capital."
            )
        elif "mean_reversion" in regime_lower:
            strategic_edge = (
                "Overextended price states indicate corrective snap-back potential; "
                "contrarian signals are given higher weight in this context."
            )
        elif "volatile" in regime_lower:
            strategic_edge = (
                "Elevated volatility requires tighter execution gates and reduced sizing."
            )
        else:
            strategic_edge = "Market state stable, following base ensemble consensus."

        reasoning += (
            f"Market is currently in a {regime_context.regime_name} regime. {strategic_edge} "
        )
        if regime_context.is_favorable:
            reasoning += "Market state is considered favorable for this strategy setup. "
        else:
            reasoning += "Market state is UNFAVORABLE/CAUTIONARY for this strategy. "

        supporting = []
        opposing = []
        for c in contributions:
            if c.contribution_score == 0:
                continue

            is_supporting = (direction > 0 and c.contribution_score > 0) or (
                direction < 0 and c.contribution_score < 0
            )
            entry = f"{c.cluster_name} ({c.contribution_score:+.2f})"

            if is_supporting:
                supporting.append(entry)
            else:
                opposing.append(entry)

        if supporting:
            reasoning += f"Strategic Confluence: High alignment from {', '.join(supporting)}. "
        if opposing:
            reasoning += f"Opposed by: {', '.join(opposing)}. "

        if not execution_summary.passed:
            reasoning += f"EXECUTION BLOCKED: {execution_summary.summary}. "
        elif not risk_assessment.passed:
            reasons = ", ".join(risk_assessment.rejection_reasons) or "Unknown risk violation"
            reasoning += f"Risk REJECTED: {reasons}. "
        else:
            reasoning += f"Passed all filters with R:R of {risk_assessment.risk_reward_ratio:.2f}."

        # 7. Machine Attribution
        machine_attr = {
            "model_confidence": confidence,
            "risk_passed": risk_assessment.passed,
            "risk_reward_ratio": risk_assessment.risk_reward_ratio,
            "risk_rejection_reasons": risk_assessment.rejection_reasons,
            "execution_passed": execution_summary.passed,
            "failed_execution_filters": [
                f.filter_name for f in execution_summary.filters if not f.passed
            ],
            "regime_confluence": regime_context.confidence,
            "regime_alignment_score": regime_context.regime_alignment_score,
            "dominant_models": dominant_models,
            "model_dominance_ratios": {
                attr.model_name: attr.dominance_ratio for attr in final_attributions
            },
            "feature_impacts": {c.cluster_name: c.contribution_score for c in contributions},
        }

        return SignalExplanation(
            signal_id=signal_id,
            symbol=symbol,
            direction=SignalDirection(direction),
            total_confidence=confidence,
            execution_summary=execution_summary,
            model_attributions=final_attributions,
            feature_contributions=contributions,
            risk_assessment=risk_assessment,
            regime_context=regime_context,
            human_readable_summary=reasoning,
            machine_attribution=machine_attr,
        )

    def get_renderable(self, explanation: SignalExplanation) -> Any:
        """
        Return a 'rich' Group containing the full breakdown.
        Used for integration with institutional dashboards.
        """
        try:
            from rich import box
            from rich.console import Group
            from rich.panel import Panel
            from rich.table import Table

            # 1. Model Votes Table
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
                vote_icon = self._get_direction_icon(attr.vote)
                model_table.add_row(
                    attr.model_name,
                    f"{vote_icon} [{vote_color}]{attr.vote.name}[/{vote_color}]",
                    f"{attr.weight:.1%}",
                    f"{attr.confidence:.1%}",
                    "⭐" if attr.is_dominant else "",
                )

            # 2. Feature Contributions
            feature_table = Table(title="Feature Cluster Contributions", box=box.SIMPLE)
            feature_table.add_column("Cluster", style="magenta")
            feature_table.add_column("Score", justify="right")
            feature_table.add_column("Impact", justify="center")
            feature_table.add_column("Summary")

            for cont in explanation.feature_contributions:
                impact_color = (
                    "red"
                    if cont.impact_level == "High"
                    else "yellow"
                    if cont.impact_level == "Medium"
                    else "dim"
                )
                impact_marker = self._get_impact_marker(cont.impact_level)
                is_confluent = (
                    explanation.direction == SignalDirection.BUY and cont.contribution_score > 0
                ) or (explanation.direction == SignalDirection.SELL and cont.contribution_score < 0)
                score_color = (
                    "green" if is_confluent else "red" if cont.contribution_score != 0 else "white"
                )
                score_icon = self._get_direction_icon(
                    1 if cont.contribution_score > 0 else -1 if cont.contribution_score < 0 else 0
                )
                feature_table.add_row(
                    cont.cluster_name,
                    f"{score_icon} [{score_color}]{cont.contribution_score:+.2f}[/{score_color}]",
                    f"[{impact_color}]{impact_marker} {cont.impact_level}[/{impact_color}]",
                    cont.summary,
                )

            # 3. Execution and Risk
            exec_table = Table(title="Execution Filters", box=box.SIMPLE, expand=True)
            exec_table.add_column("Filter")
            exec_table.add_column("Status", justify="center")
            exec_table.add_column("Details")

            for f in explanation.execution_summary.filters:
                status = "[green]OK[/green]" if f.passed else "[red]FAIL[/red]"
                details = f.message or f"Value: {f.value} (Thr: {f.threshold})"
                exec_table.add_row(f.filter_name, status, details)

            risk_status = (
                "[bold green]PASSED[/bold green]"
                if explanation.risk_assessment.passed
                else "[bold red]REJECTED[/bold red]"
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

            components = [model_table]
            if explanation.feature_contributions:
                components.append(feature_table)
            if explanation.execution_summary.filters:
                components.append(exec_table)

            components.append(Panel(risk_info, title="Risk Assessment"))
            components.append(Panel(regime_info, title="Market Context"))

            return Group(*components)
        except ImportError:
            return None

    def format_for_terminal(
        self, explanation: SignalExplanation, console: Any | None = None
    ) -> str:
        """
        Format the explanation for terminal display using 'rich'.
        """
        try:
            from rich import box
            from rich.console import Console
            from rich.panel import Panel

            if console is None:
                console = Console(force_terminal=True)

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

            renderable = self.get_renderable(explanation)
            if renderable is None:
                return self._get_plain_text_explanation(explanation)

            with console.capture() as capture:
                console.print(header)
                console.print(renderable)

            return capture.get()

        except ImportError:
            return self._get_plain_text_explanation(explanation)

    def _get_plain_text_explanation(self, explanation: SignalExplanation) -> str:
        """Fallback plain text formatter for non-interactive environments."""
        output = "=== TRADE SIGNAL EXPLANATION ===\n"
        output += f"Symbol: {explanation.symbol} | Direction: {explanation.direction.name} | Conf: {explanation.total_confidence:.1%}\n"
        output += f"Summary: {explanation.human_readable_summary}\n\n"

        output += "Model Votes:\n"
        for attr in explanation.model_attributions:
            output += (
                f"  - {attr.model_name}: {attr.vote.name} (W={attr.weight:.1%}, "
                f"C={attr.confidence:.1%}) {'[DOMINANT]' if attr.is_dominant else ''}\n"
            )

        if explanation.feature_contributions:
            output += "\nFeature Contributions:\n"
            for cont in explanation.feature_contributions:
                output += (
                    f"  - {cont.cluster_name}: {cont.contribution_score:+.2f} "
                    f"({cont.impact_level}) - {cont.summary}\n"
                )

        if explanation.execution_summary.filters:
            output += (
                f"\nExecution: {'PASSED' if explanation.execution_summary.passed else 'BLOCKED'}\n"
            )
            for f in explanation.execution_summary.filters:
                output += f"  - {f.filter_name}: {'OK' if f.passed else 'FAIL'} ({f.message or f.value})\n"

        output += (
            f"\nRisk Assessment: {'PASSED' if explanation.risk_assessment.passed else 'REJECTED'}\n"
        )
        output += f"Regime: {explanation.regime_context.regime_name} ({explanation.regime_context.volatility_state})\n"
        return output
