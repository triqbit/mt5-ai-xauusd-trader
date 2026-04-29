"""
Tests for the explainability module.
"""

import pytest
from datetime import datetime
from src.core.explainability import SignalExplainer, SignalExplanation

def test_signal_explainer_success():
    explainer = SignalExplainer()

    symbol = "XAUUSD"
    direction = 1
    confidence = 0.85
    model_outputs = {"ppo": 0.8, "lstm": 0.9}
    weights = {"ppo": 0.5, "lstm": 0.5}
    regime_data = {
        "regime": "TRENDING_UP",
        "volatility": "LOW",
        "trend_strength": 0.8,
        "is_favorable": True
    }
    risk_results = {
        "passed": True,
        "filters": ["daily_loss", "max_pos"],
        "rr": 2.1,
        "threshold": 0.55
    }
    feature_importance = {
        "EMA_20": 0.4,
        "RSI_14": 0.3,
        "ATR_14": 0.2,
        "Volume": 0.1
    }

    explanation = explainer.explain(
        symbol=symbol,
        direction=direction,
        confidence=confidence,
        model_outputs=model_outputs,
        weights=weights,
        regime_data=regime_data,
        risk_results=risk_results,
        feature_importance=feature_importance
    )

    assert isinstance(explanation, SignalExplanation)
    assert explanation.symbol == symbol
    assert explanation.direction == direction
    assert explanation.models.consensus_score == confidence
    assert explanation.risk.passed_all is True
    assert "Strong BUY signal" in explanation.summary
    assert "TRENDING_UP" in explanation.summary
    assert explanation.features.trend > 0
    assert len(explanation.features.top_features) > 0

def test_signal_explainer_rejection():
    explainer = SignalExplainer()

    risk_results = {
        "passed": False,
        "reason": "Risk-Reward ratio too low",
        "rr": 1.2,
        "threshold": 0.55
    }

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=-1,
        confidence=0.6,
        model_outputs={"ppo": 0.6},
        weights={"ppo": 1.0},
        regime_data={"regime": "RANGING", "volatility": "HIGH", "trend_strength": 0.2},
        risk_results=risk_results
    )

    assert explanation.risk.passed_all is False
    assert "REJECTED" in explanation.summary
    assert "Risk-Reward ratio too low" in explanation.summary

def test_feature_attribution_clustering():
    explainer = SignalExplainer()
    importance = {
        "EMA_TREND": 0.5,
        "SMA_50": 0.2,
        "ATR_VOL": 0.3,
        "RSI_MOMO": 0.4,
        "VOL_SUM": 0.1
    }

    attr = explainer._build_feature_attribution(importance)

    assert attr.trend == 0.7  # 0.5 + 0.2
    assert attr.volatility == 0.3
    assert attr.momentum == 0.4
    assert attr.volume == 0.1
    assert len(attr.top_features) == 5
