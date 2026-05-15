"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_regime_adaptive_safety.py
Integration tests for Regime-Adaptive Safety Hardening.
"""

from datetime import UTC, datetime

import pytest

from src.core.config import TradingConfig
from src.core.constants import MarketRegime
from src.core.schemas import RegimeInfo, TradeSignal
from src.trading.execution_filter import ExecutionFilter


@pytest.fixture
def config():
    return TradingConfig(
        MT5_PASSWORD="fake_password",
        MT5_SERVER="fake_server",
        min_confidence=0.55,
        model_drift_threshold=0.30,
        model_accuracy_floor=0.50,
    )


@pytest.fixture
def filter_engine(config):
    return ExecutionFilter(config=config)


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
        confidence=0.60,  # Below NEWS_SHOCK and BREAKOUT requirements, but above base
        timestamp=datetime.now(UTC),
    )


# --- Layer 12: Regime Stability Tests ---


def test_regime_stability_pass(filter_engine):
    regime = RegimeInfo(
        label=MarketRegime.RANGING,
        confidence=0.9,
        transition_score=0.5,  # Stable
        volatility_index=1.0,
    )
    passed, metrics = filter_engine._check_regime_stability_with_metrics(regime)
    assert passed is True
    assert metrics["transition_score"] == 0.5


def test_regime_stability_fail(filter_engine):
    regime = RegimeInfo(
        label=MarketRegime.RANGING,
        confidence=0.4,
        transition_score=0.85,  # Unstable
        volatility_index=1.0,
    )
    passed, metrics = filter_engine._check_regime_stability_with_metrics(regime)
    assert passed is False
    assert metrics["transition_score"] == 0.85


# --- Adaptive Confidence Threshold Tests ---


def test_confidence_adaptive_ranging(filter_engine, base_signal):
    # RANGING should use base threshold (0.55). base_signal (0.60) should pass.
    regime = RegimeInfo(
        label=MarketRegime.RANGING,
        confidence=0.9,
        transition_score=0.1,
        volatility_index=1.0,
    )
    passed, metrics = filter_engine._check_confidence_threshold_with_metrics(
        base_signal, regime_info=regime
    )
    assert passed is True
    assert metrics["threshold"] == 0.55


def test_confidence_adaptive_news_shock_fail(filter_engine, base_signal):
    # NEWS_SHOCK raises threshold to 0.70. base_signal (0.60) should fail.
    regime = RegimeInfo(
        label=MarketRegime.NEWS_SHOCK,
        confidence=0.9,
        transition_score=0.1,
        volatility_index=3.0,
    )
    passed, metrics = filter_engine._check_confidence_threshold_with_metrics(
        base_signal, regime_info=regime
    )
    assert passed is False
    assert metrics["threshold"] == 0.70
    assert metrics["is_hardened"] is True


def test_confidence_adaptive_news_shock_pass(filter_engine):
    # High confidence signal should still pass in NEWS_SHOCK
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.75,
    )
    regime = RegimeInfo(
        label=MarketRegime.NEWS_SHOCK,
        confidence=0.9,
        transition_score=0.1,
        volatility_index=3.0,
    )
    passed, metrics = filter_engine._check_confidence_threshold_with_metrics(
        signal, regime_info=regime
    )
    assert passed is True
    assert metrics["threshold"] == 0.70


def test_confidence_adaptive_breakout_fail(filter_engine, base_signal):
    # VOLATILE_BREAKOUT raises threshold to 0.65. base_signal (0.60) should fail.
    regime = RegimeInfo(
        label=MarketRegime.VOLATILE_BREAKOUT,
        confidence=0.9,
        transition_score=0.1,
        volatility_index=1.5,
    )
    passed, metrics = filter_engine._check_confidence_threshold_with_metrics(
        base_signal, regime_info=regime
    )
    assert passed is False
    assert metrics["threshold"] == 0.65


# --- Adaptive Model Stability Tests ---


def test_model_stability_adaptive_ranging(filter_engine):
    # RANGING uses base: drift 0.30, accuracy 0.50.
    # Health: drift 0.25, accuracy 0.55 should pass.
    regime = RegimeInfo(
        label=MarketRegime.RANGING,
        confidence=0.9,
        transition_score=0.1,
        volatility_index=1.0,
    )
    health = {"drift": 0.25, "accuracy": 0.55}
    passed, metrics = filter_engine._check_model_stability_with_metrics(health, regime_info=regime)
    assert passed is True
    assert metrics["drift_threshold"] == 0.30
    assert metrics["accuracy_floor"] == 0.50
    assert metrics["is_hardened"] is False


def test_model_stability_adaptive_news_shock_fail_drift(filter_engine):
    # NEWS_SHOCK tightens: drift 0.20, accuracy 0.55.
    # Health: drift 0.25, accuracy 0.60 should fail on drift.
    regime = RegimeInfo(
        label=MarketRegime.NEWS_SHOCK,
        confidence=0.9,
        transition_score=0.1,
        volatility_index=3.0,
    )
    health = {"drift": 0.25, "accuracy": 0.60}
    passed, metrics = filter_engine._check_model_stability_with_metrics(health, regime_info=regime)
    assert passed is False
    assert pytest.approx(metrics["drift_threshold"]) == 0.20
    assert metrics["is_hardened"] is True


def test_model_stability_adaptive_news_shock_fail_accuracy(filter_engine):
    # NEWS_SHOCK tightens: drift 0.20, accuracy 0.55.
    # Health: drift 0.15, accuracy 0.52 should fail on accuracy.
    regime = RegimeInfo(
        label=MarketRegime.NEWS_SHOCK,
        confidence=0.9,
        transition_score=0.1,
        volatility_index=3.0,
    )
    health = {"drift": 0.15, "accuracy": 0.52}
    passed, metrics = filter_engine._check_model_stability_with_metrics(health, regime_info=regime)
    assert passed is False
    assert metrics["accuracy_floor"] == 0.55


# --- Full Validation Cascade with Regime ---


def test_full_validate_blocked_by_regime_stability(filter_engine, base_signal):
    # Signal and market data are fine, but regime is unstable
    regime = RegimeInfo(
        label=MarketRegime.TRENDING,
        confidence=0.5,
        transition_score=0.9,  # BLOCKS HERE
        volatility_index=1.0,
    )
    # Mock precomputed to pass other layers
    precomputed = {
        "atr_volatility": {"current_atr": 1.0, "avg_atr": 1.0},
        "trend_angle": {"slope": 1.0},
        "ema_sequence": {"emas": {8: 104, 21: 103, 50: 102, 200: 101}},
        "momentum": {"rsi": 60.0},
    }

    decision = filter_engine.validate(
        base_signal,
        precomputed_metrics=precomputed,
        regime_info=regime,
    )

    assert decision.is_approved is False
    assert decision.blocked_by == "REGIME_UNSTABLE"
    assert decision.trace["regime_stability"]["passed"] is False


def test_full_validate_hardened_confidence_block(filter_engine, base_signal):
    # base_signal has 0.60 confidence. In NEWS_SHOCK, it should be blocked by CONFIDENCE_THRESHOLD (0.70 req).
    regime = RegimeInfo(
        label=MarketRegime.NEWS_SHOCK,
        confidence=0.9,
        transition_score=0.1,
        volatility_index=1.0,
    )
    precomputed = {
        "atr_volatility": {"current_atr": 1.0, "avg_atr": 1.0},
        "trend_angle": {"slope": 1.0},
        "ema_sequence": {"emas": {8: 104, 21: 103, 50: 102, 200: 101}},
        "momentum": {"rsi": 60.0},
    }

    decision = filter_engine.validate(
        base_signal,
        precomputed_metrics=precomputed,
        regime_info=regime,
    )

    assert decision.is_approved is False
    assert decision.blocked_by == "CONFIDENCE_THRESHOLD"
    assert decision.trace["confidence_threshold"]["threshold"] == 0.70
