"""
Unit tests for the explainability module.
"""

from src.core.explainability import (
    SignalDirection,
    SignalExplainer,
    SignalExplanation,
)


def test_signal_explanation_pydantic_validation():
    """Test that SignalExplanation correctly validates its fields."""
    data = {
        "symbol": "XAUUSD",
        "direction": 1,
        "total_confidence": 0.85,
        "execution_summary": {
            "passed": True,
            "filters": [{"filter_name": "Spread", "passed": True, "value": 0.5}],
            "summary": "Execution OK",
        },
        "model_attributions": [
            {"model_name": "PPO", "vote": 1, "confidence": 0.85, "weight": 0.6, "is_dominant": True}
        ],
        "feature_contributions": [
            {
                "cluster_name": "Trend",
                "contribution_score": 0.8,
                "impact_level": "High",
                "summary": "Strong trend",
            }
        ],
        "risk_assessment": {
            "passed": True,
            "risk_reward_ratio": 2.5,
            "drawdown_impact_pct": 0.05,
            "summary": "Risk acceptable",
        },
        "regime_context": {
            "regime_name": "Trending",
            "confidence": 0.9,
            "volatility_state": "Normal",
            "is_favorable": True,
            "summary": "Favorable trend",
        },
        "human_readable_summary": "Buy signal due to trend.",
        "machine_attribution": {"conf": 0.85},
    }

    explanation = SignalExplanation(**data)
    assert explanation.symbol == "XAUUSD"
    assert explanation.direction == SignalDirection.BUY
    assert explanation.execution_summary.passed is True
    assert len(explanation.model_attributions) == 1
    assert explanation.model_attributions[0].is_dominant is True


def test_signal_explainer_aggregation():
    """Test that SignalExplainer correctly aggregates data from various sources."""
    explainer = SignalExplainer()

    symbol = "XAUUSD"
    direction = 1
    confidence = 0.75
    model_votes = {"ppo": 0, "lstm": 0}  # 0=buy in ensemble.py mapping
    model_weights = {"ppo": 0.7, "lstm": 0.3}
    risk_data = {
        "passed": True,
        "risk_reward": 2.1,
        "drawdown_impact": 0.02,
        "kelly_fraction": 0.1,
        "summary": "Risk clear",
    }
    regime_info = {
        "name": "Trending",
        "confidence": 0.88,
        "volatility": "Normal",
        "is_favorable": True,
        "summary": "Strong momentum",
    }
    execution_data = {
        "passed": True,
        "filters": [{"name": "Spread", "passed": True, "value": 0.2, "threshold": 1.0}],
        "summary": "Spread tight",
    }

    explanation = explainer.explain(
        symbol=symbol,
        direction=direction,
        confidence=confidence,
        model_votes=model_votes,
        model_weights=model_weights,
        risk_data=risk_data,
        regime_info=regime_info,
        execution_data=execution_data,
    )

    assert explanation.symbol == symbol
    assert explanation.direction == SignalDirection.BUY
    assert explanation.total_confidence == confidence
    assert explanation.execution_summary.passed is True
    assert len(explanation.model_attributions) == 2

    # Check dominant model (ppo has higher weight)
    ppo_attr = next(a for a in explanation.model_attributions if a.model_name == "ppo")
    assert ppo_attr.is_dominant is True

    assert explanation.risk_assessment.passed is True
    assert explanation.regime_context.regime_name == "Trending"
    assert "Ensemble generated a BUY signal" in explanation.human_readable_summary


def test_signal_explainer_execution_blocked():
    """Test explanation generation for a signal blocked by execution filters."""
    explainer = SignalExplainer()

    execution_data = {
        "passed": False,
        "filters": [{"name": "Spread", "passed": False, "value": 3.0, "threshold": 2.0}],
        "summary": "High spread",
    }

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.8,
        model_votes={"ppo": 0},
        model_weights={"ppo": 1.0},
        risk_data={"passed": True, "risk_reward": 2.0, "summary": "Risk OK"},
        regime_info={"name": "Bullish"},
        execution_data=execution_data,
    )

    assert explanation.execution_summary.passed is False
    assert "EXECUTION BLOCKED: High spread" in explanation.human_readable_summary


def test_signal_explainer_risk_rejection():
    """Test explanation generation for a signal rejected by risk filters."""
    explainer = SignalExplainer()

    risk_data = {
        "passed": False,
        "rejection_reasons": ["Daily loss limit reached"],
        "risk_reward": 1.2,
        "drawdown_impact": 0.0,
        "summary": "Rejected by risk manager",
    }

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=-1,
        confidence=0.6,
        model_votes={"ppo": 1},  # 1=sell
        model_weights={"ppo": 1.0},
        risk_data=risk_data,
        regime_info={"name": "Volatile"},
    )

    assert explanation.direction == SignalDirection.SELL
    assert explanation.risk_assessment.passed is False
    assert "Daily loss limit reached" in explanation.risk_assessment.rejection_reasons
    assert "Risk REJECTED" in explanation.human_readable_summary


def test_format_for_terminal_fallback():
    """Test terminal formatting (plain text fallback if rich is not used or available)."""
    explainer = SignalExplainer()
    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.9,
        model_votes={"ppo": 0},
        model_weights={"ppo": 1.0},
        risk_data={"passed": True, "risk_reward": 3.0, "summary": "Ok"},
        regime_info={"name": "Bullish"},
        execution_data={
            "passed": True,
            "filters": [{"name": "Spread", "passed": True, "value": 0.5}],
            "summary": "OK",
        },
    )

    formatted = explainer.format_for_terminal(explanation)
    # Check for presence of key info regardless of formatting (rich vs plain)
    assert "XAUUSD" in formatted
    assert "BUY" in formatted
    assert "ppo" in formatted
    assert "Execution" in formatted or "EXECUTION" in formatted.upper()
    assert "Risk Assessment" in formatted or "RISK" in formatted.upper()
