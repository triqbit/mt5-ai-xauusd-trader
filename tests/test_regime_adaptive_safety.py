"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_regime_adaptive_safety.py
Unit tests for regime-adaptive safety hardening in ExecutionFilter.
"""

from datetime import datetime, UTC
import pytest
from src.core.schemas import TradeSignal
from src.trading.execution_filter import ExecutionFilter
from src.models.regime_detector import MarketRegime, RegimeInfo

@pytest.fixture
def filter_engine():
    return ExecutionFilter(max_drawdown=0.12)

@pytest.fixture
def base_signal():
    return TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.60  # Default threshold is 0.55
    )

def test_regime_stability_pass(filter_engine):
    regime_info = RegimeInfo(
        label=MarketRegime.RANGING,
        confidence=0.9,
        transition_score=0.2, # Stable
        volatility_index=1.0,
        transition_probabilities={},
        raw_features={}
    )
    passed, metrics = filter_engine._check_regime_stability_with_metrics(regime_info)
    assert passed is True
    assert metrics["transition_score"] == 0.2

def test_regime_stability_block(filter_engine):
    regime_info = RegimeInfo(
        label=MarketRegime.RANGING,
        confidence=0.5,
        transition_score=0.85, # Highly unstable
        volatility_index=1.0,
        transition_probabilities={},
        raw_features={}
    )
    passed, metrics = filter_engine._check_regime_stability_with_metrics(regime_info)
    assert passed is False
    assert metrics["transition_score"] == 0.85

def test_adaptive_confidence_news_shock_block(filter_engine, base_signal):
    # base_signal has confidence 0.60
    # NEWS_SHOCK requires 0.70
    regime_info = RegimeInfo(
        label=MarketRegime.NEWS_SHOCK,
        confidence=0.8,
        transition_score=0.1,
        volatility_index=2.5,
        transition_probabilities={},
        raw_features={}
    )
    passed, metrics = filter_engine._check_confidence_threshold_with_metrics(base_signal, regime_info)
    assert passed is False
    assert metrics["threshold"] == 0.70

def test_adaptive_confidence_news_shock_pass(filter_engine):
    high_conf_signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.75
    )
    regime_info = RegimeInfo(
        label=MarketRegime.NEWS_SHOCK,
        confidence=0.8,
        transition_score=0.1,
        volatility_index=2.5,
        transition_probabilities={},
        raw_features={}
    )
    passed, metrics = filter_engine._check_confidence_threshold_with_metrics(high_conf_signal, regime_info)
    assert passed is True
    assert metrics["threshold"] == 0.70

def test_adaptive_confidence_breakout_block(filter_engine, base_signal):
    # base_signal has confidence 0.60
    # VOLATILE_BREAKOUT requires 0.65
    regime_info = RegimeInfo(
        label=MarketRegime.VOLATILE_BREAKOUT,
        confidence=0.8,
        transition_score=0.1,
        volatility_index=1.5,
        transition_probabilities={},
        raw_features={}
    )
    passed, metrics = filter_engine._check_confidence_threshold_with_metrics(base_signal, regime_info)
    assert passed is False
    assert metrics["threshold"] == 0.65

def test_adaptive_model_stability_hardening(filter_engine):
    # Normal thresholds: drift <= 0.3, accuracy >= 0.45
    # NEWS_SHOCK hardening: drift <= 0.2, accuracy >= 0.50
    model_health = {"drift": 0.25, "accuracy": 0.48}

    # Normal regime
    passed_normal, metrics_normal = filter_engine._check_model_stability_with_metrics(model_health)
    assert passed_normal is True
    assert metrics_normal["drift_threshold"] == 0.3
    assert metrics_normal["accuracy_floor"] == 0.45

    # NEWS_SHOCK regime
    regime_info = RegimeInfo(
        label=MarketRegime.NEWS_SHOCK,
        confidence=0.8,
        transition_score=0.1,
        volatility_index=2.5,
        transition_probabilities={},
        raw_features={}
    )
    passed_shock, metrics_shock = filter_engine._check_model_stability_with_metrics(model_health, regime_info)
    assert passed_shock is False
    assert abs(metrics_shock["drift_threshold"] - 0.2) < 1e-9
    assert abs(metrics_shock["accuracy_floor"] - 0.50) < 1e-9

def test_full_cascade_regime_stability_block(filter_engine, base_signal):
    # High transition score should block via Layer 12
    regime_info = RegimeInfo(
        label=MarketRegime.TRENDING,
        confidence=0.8,
        transition_score=0.9, # Unstable
        volatility_index=1.0,
        transition_probabilities={},
        raw_features={}
    )

    # We need to mock other layers or provide precomputed to avoid failure in earlier layers
    precomputed = {
        "atr_volatility": {"current_atr": 1.0, "avg_atr": 1.0, "ratio": 1.0},
        "trend_angle": {"slope": 1.0},
        "ema_sequence": {"emas": {8: 104, 21: 103, 50: 102, 200: 101}},
        "momentum": {"rsi": 60.0},
    }

    decision = filter_engine.validate(
        base_signal,
        current_drawdown=0.01,
        timestamp=datetime.now(UTC),
        precomputed_metrics=precomputed,
        regime_info=regime_info
    )

    assert decision.is_approved is False
    assert decision.blocked_by == "REGIME_UNSTABLE"
    assert decision.trace["regime_stability"]["passed"] is False
