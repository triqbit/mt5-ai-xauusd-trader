"""
Tests for the explainability module.
"""

import pytest
from datetime import datetime, timezone
from src.core.explainability import (
    SignalExplainer,
    ModelAttribution,
    FilterResult,
    RegimeContext,
    RiskConstraintInfo,
)


def test_signal_explanation_generation():
    explainer = SignalExplainer()

    attributions = [
        ModelAttribution(algo_name="ppo", contribution_weight=0.5, direction_signal=1, confidence=0.8),
        ModelAttribution(algo_name="lstm", contribution_weight=0.5, direction_signal=1, confidence=0.6),
    ]

    filters = [
        FilterResult(filter_name="volatility_check", passed=True, value=1.2, threshold=2.0, message="Normal volatility"),
    ]

    regime = RegimeContext(regime_type="Trending", confidence=0.9, key_features={"slope": 0.05})

    risk = RiskConstraintInfo(
        account_balance=10000.0,
        risk_per_trade=0.01,
        max_drawdown_limit=0.15,
        current_drawdown=0.02,
        is_circuit_breaker_active=False
    )

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        attributions=attributions,
        filters=filters,
        regime=regime,
        risk=risk
    )

    assert explanation.symbol == "XAUUSD"
    assert explanation.direction == 1
    assert "BUY signal generated" in explanation.summary
    assert "100% ensemble consensus" in explanation.summary
    assert "Primary driver: ppo" in explanation.summary
    assert "Trending regime" in explanation.summary
    assert explanation.regime.regime_type == "Trending"
    assert len(explanation.model_attributions) == 2


def test_failed_filter_summary():
    explainer = SignalExplainer()

    attributions = [
        ModelAttribution(algo_name="ppo", contribution_weight=1.0, direction_signal=-1, confidence=0.7),
    ]

    filters = [
        FilterResult(filter_name="spread_filter", passed=False, value=50, threshold=20, message="Spread too high"),
    ]

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=-1,
        attributions=attributions,
        filters=filters
    )

    assert "SELL signal generated" in explanation.summary
    assert "Caution: Failed filters: spread_filter" in explanation.summary


def test_neutral_signal_summary():
    explainer = SignalExplainer()
    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=0,
        attributions=[],
        filters=[]
    )

    assert "No trading signal generated: Neutral state" in explanation.summary
