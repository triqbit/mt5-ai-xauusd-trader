"""
Tests for the Trade Explainer module.
"""

import pytest
from src.core.explainability import TradeExplainer, TradeExplanation


def test_explain_approval():
    explainer = TradeExplainer()

    symbol = "XAUUSD"
    direction = 1
    confidence = 0.85

    model_results = [
        {"model_name": "PPO", "weight": 0.4, "direction": 1, "confidence": 0.9, "raw_probs": {"0": 0.9, "1": 0.05, "2": 0.05}},
        {"model_name": "LSTM", "weight": 0.6, "direction": 1, "confidence": 0.8, "raw_probs": {"0": 0.8, "1": 0.1, "2": 0.1}}
    ]

    filter_results = [
        {"filter_name": "Trend", "passed": True, "message": "Trend is bullish"},
        {"filter_name": "Volatility", "passed": True, "message": "Volatility is within limits"}
    ]

    regime = {
        "regime": "trending",
        "confidence": 0.95,
        "description": "Strong bullish trend"
    }

    risk_status = [
        {"name": "Drawdown", "limit": 0.15, "actual": 0.02, "status": "OK"}
    ]

    feature_importance = {
        "momentum": 0.7,
        "volatility": 0.2,
        "trend": 0.1
    }

    explanation = explainer.explain(
        symbol=symbol,
        direction=direction,
        confidence=confidence,
        model_results=model_results,
        filter_results=filter_results,
        regime=regime,
        risk_status=risk_status,
        feature_importance=feature_importance
    )

    assert isinstance(explanation, TradeExplanation)
    assert explanation.symbol == symbol
    assert explanation.direction == direction
    assert explanation.confidence == confidence
    assert "Strong BUY signal" in explanation.summary
    assert "trending market" in explanation.summary
    assert len(explanation.model_outputs) == 2
    assert len(explanation.execution_filters) == 2
    assert explanation.regime_context.regime == "trending"
    assert explanation.attribution["momentum"] == 0.7


def test_explain_rejection():
    explainer = TradeExplainer()

    filter_results = [
        {"filter_name": "Trend", "passed": False, "message": "Trend is bearish"},
    ]

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.6,
        filter_results=filter_results
    )

    assert "REJECTED BUY" in explanation.summary
    assert "due to: Trend is bearish" in explanation.summary


def test_to_dict():
    explainer = TradeExplainer()
    explanation = explainer.explain("XAUUSD", 1, 0.7)

    d = explanation.to_dict()
    assert isinstance(d, dict)
    assert d["symbol"] == "XAUUSD"
    assert d["direction"] == 1
    assert "timestamp" in d
