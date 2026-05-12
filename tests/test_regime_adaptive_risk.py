"""
Tests for Regime-Adaptive Model Health Guardrails in RiskManager.
Verifies that model health thresholds are correctly tightened during unstable market states.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.core.config import TradingConfig
from src.core.constants import SignalDirection
from src.core.schemas import TradeSignal
from src.models.regime_detector import MarketRegime, RegimeInfo
from src.trading.risk_manager import RiskManager


@pytest.fixture
def mock_config():
    cfg = MagicMock(spec=TradingConfig)
    cfg.model_drift_threshold = 0.3
    cfg.model_accuracy_floor = 0.5
    cfg.model_calibration_threshold = 0.25
    cfg.max_losing_streak = 3
    cfg.max_daily_loss = 0.05
    cfg.max_positions = 5
    cfg.risk_per_trade = 0.01
    return cfg


@pytest.fixture
def risk_manager(mock_config):
    return RiskManager(mock_config, account_balance=10000.0)


@pytest.fixture
def base_signal():
    return TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.7,
        timestamp=datetime.now(timezone.utc),
    )


def test_check_model_health_ranging(risk_manager):
    """Verifies that base thresholds are used in RANGING regime."""
    regime_info = RegimeInfo(
        label=MarketRegime.RANGING, confidence=0.9, transition_score=0.1, volatility_index=1.0
    )

    # Moderate drift (0.25) is below base threshold (0.3)
    health = {"drift": 0.25, "accuracy": 0.55, "calibration": 0.1}
    assert risk_manager._check_model_health(health, regime_info=regime_info) is True

    # High drift (0.35) is above base threshold
    health = {"drift": 0.35, "accuracy": 0.55, "calibration": 0.1}
    assert risk_manager._check_model_health(health, regime_info=regime_info) is False


def test_check_model_health_news_shock(risk_manager):
    """Verifies that thresholds are tightened during NEWS_SHOCK."""
    regime_info = RegimeInfo(
        label=MarketRegime.NEWS_SHOCK, confidence=0.9, transition_score=0.1, volatility_index=3.0
    )

    # Moderate drift (0.25) was OK in RANGING, but should be REJECTED in NEWS_SHOCK
    # because NEWS_SHOCK tightens drift threshold by 50% (0.3 -> 0.15)
    health = {"drift": 0.25, "accuracy": 0.55, "calibration": 0.1}
    assert risk_manager._check_model_health(health, regime_info=regime_info) is False

    # Low drift (0.1) should still pass
    health = {"drift": 0.1, "accuracy": 0.7, "calibration": 0.1}
    assert risk_manager._check_model_health(health, regime_info=regime_info) is True

    # Low accuracy (0.55) was OK in RANGING, but should be REJECTED in NEWS_SHOCK
    # because NEWS_SHOCK increases accuracy floor by 10% (0.5 -> 0.6)
    health = {"drift": 0.1, "accuracy": 0.55, "calibration": 0.1}
    assert risk_manager._check_model_health(health, regime_info=regime_info) is False


def test_check_model_health_volatile_breakout(risk_manager):
    """Verifies that drift threshold is tightened during VOLATILE_BREAKOUT."""
    regime_info = RegimeInfo(
        label=MarketRegime.VOLATILE_BREAKOUT,
        confidence=0.9,
        transition_score=0.1,
        volatility_index=1.8,
    )

    # Moderate drift (0.25) was OK in RANGING, but should be REJECTED in VOLATILE_BREAKOUT
    # because it tightens drift by 25% (0.3 -> 0.225)
    health = {"drift": 0.25, "accuracy": 0.55, "calibration": 0.1}
    assert risk_manager._check_model_health(health, regime_info=regime_info) is False

    # Drift 0.2 should pass (0.2 < 0.225)
    health = {"drift": 0.2, "accuracy": 0.55, "calibration": 0.1}
    assert risk_manager._check_model_health(health, regime_info=regime_info) is True


def test_approve_cascade_with_regime(risk_manager, base_signal):
    """Verifies that the full approve() cascade respects the regime-adaptive health."""
    regime_info = RegimeInfo(
        label=MarketRegime.NEWS_SHOCK, confidence=0.9, transition_score=0.1, volatility_index=3.0
    )

    # Case 1: Health is OK for RANGING but not for NEWS_SHOCK
    health = {"drift": 0.25, "accuracy": 0.55, "calibration": 0.1}

    # Mock other checks to pass
    risk_manager._check_circuit_breaker = MagicMock(return_value=True)
    risk_manager._check_daily_loss = MagicMock(return_value=True)
    risk_manager._check_max_positions = MagicMock(return_value=True)
    risk_manager._check_symbol_allocation = MagicMock(return_value=True)
    risk_manager._check_minimum_confidence = MagicMock(return_value=True)
    risk_manager._check_risk_reward = MagicMock(return_value=True)
    risk_manager._check_consecutive_losses = MagicMock(return_value=True)

    # Should be rejected due to health in NEWS_SHOCK
    assert risk_manager.approve(base_signal, model_health=health, regime_info=regime_info) is False

    # Should be approved if we change to RANGING
    ranging_info = RegimeInfo(
        label=MarketRegime.RANGING, confidence=0.9, transition_score=0.1, volatility_index=1.0
    )
    assert risk_manager.approve(base_signal, model_health=health, regime_info=ranging_info) is True
