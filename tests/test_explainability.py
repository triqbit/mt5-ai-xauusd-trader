"""
Unit tests for the explainability module.
"""
from src.core.explainability import SignalExplainer, SignalExplanation


def test_explainer_basic_buy():
    explainer = SignalExplainer()
    symbol = "XAUUSD"
    direction = 1
    confidence = 0.85
    model_outputs = {
        "ppo": {"confidence": 0.8},
        "lstm": {"confidence": 0.9}
    }
    risk_reasons = []
    market_data = {
        "regime": "Trending",
        "volatility": "Low"
    }
    feature_importance = {
        "rsi_14": 0.5,
        "atr_14": 0.2
    }

    explanation = explainer.explain(
        symbol, direction, confidence, model_outputs, risk_reasons, market_data, feature_importance
    )

    assert isinstance(explanation, SignalExplanation)
    assert explanation.symbol == symbol
    assert explanation.direction == direction
    assert explanation.overall_confidence == confidence
    assert "BUY" in explanation.summary
    assert "Trending" in explanation.summary
    assert len(explanation.models) == 2
    assert explanation.market_context.regime == "Trending"

    # Check attribution
    ppo_attr = next(m for m in explanation.models if m.algorithm == "ppo")
    assert len(ppo_attr.contributions) == 2
    rsi_item = next(c for c in ppo_attr.contributions if c.name == "rsi_14")
    assert rsi_item.cluster == "Momentum"
    assert rsi_item.contribution == 0.5


def test_explainer_rejection():
    explainer = SignalExplainer()
    symbol = "XAUUSD"
    direction = -1
    confidence = 0.7
    model_outputs = {"ensemble": {"confidence": 0.7}}
    risk_reasons = ["Max positions reached", "Risk-Reward ratio too low"]

    explanation = explainer.explain(
        symbol, direction, confidence, model_outputs, risk_reasons
    )

    assert "REJECTED" in explanation.summary
    assert "Max positions reached" in explanation.summary

    # Check filters
    max_pos_filter = next(f for f in explanation.execution_filters if f.filter_name == "Max Positions")
    assert max_pos_filter.passed is False
    assert max_pos_filter.reason == "Max positions reached"

    rr_filter = next(f for f in explanation.execution_filters if f.filter_name == "Risk-Reward")
    assert rr_filter.passed is False

    cb_filter = next(f for f in explanation.execution_filters if f.filter_name == "Circuit Breaker")
    assert cb_filter.passed is True
