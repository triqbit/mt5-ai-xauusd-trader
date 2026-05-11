"""
Tests for Regime-Adaptive Risk Guardrails.
Verifies that RiskManager tightens thresholds during unstable market regimes.
"""

import pytest
from unittest.mock import MagicMock
from src.trading.risk_manager import RiskManager
from src.models.regime_detector import MarketRegime, RegimeInfo
from src.core.schemas import TradeSignal
from src.core.config import TradingConfig

@pytest.fixture
def mock_config():
    cfg = MagicMock(spec=TradingConfig)
    cfg.max_daily_loss = 0.05
    cfg.max_positions = 5
    cfg.risk_per_trade = 0.01
    cfg.min_confidence = 0.55
    cfg.max_losing_streak = 3
    cfg.model_drift_threshold = 0.3
    cfg.model_accuracy_floor = 0.5
    cfg.model_calibration_threshold = 0.25
    cfg.max_drawdown = 0.15
    return cfg

@pytest.fixture
def mock_signal():
    return TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        confidence=0.7,
        algorithm="ensemble"
    )

def test_risk_manager_regime_adaptive_news_shock(mock_config, mock_signal):
    """Verify that RiskManager tightens thresholds in NEWS_SHOCK."""
    rm = RiskManager(mock_config, account_balance=10000.0)

    # Borderline health: would pass in normal regime (drift=0.2 < 0.3, acc=0.52 > 0.5)
    health = {"drift": 0.2, "accuracy": 0.52, "calibration": 0.1}

    # Normal regime (UNKNOWN/RANGING) should approve
    assert rm.approve(mock_signal, model_health=health) is True

    # NEWS_SHOCK regime should tighten:
    # drift_limit = 0.3 * 0.5 = 0.15 (so drift=0.2 should fail)
    # accuracy_floor = 0.5 + 0.05 = 0.55 (so accuracy=0.52 should fail)
    news_regime = RegimeInfo(
        label=MarketRegime.NEWS_SHOCK,
        confidence=0.9,
        transition_score=0.1,
        volatility_index=2.5
    )

    assert rm.approve(mock_signal, model_health=health, regime_info=news_regime) is False

def test_risk_manager_regime_adaptive_volatile_breakout(mock_config, mock_signal):
    """Verify that RiskManager tightens drift limit in VOLATILE_BREAKOUT."""
    rm = RiskManager(mock_config, account_balance=10000.0)

    # Borderline drift: 0.25 < 0.3 (normal)
    health = {"drift": 0.25, "accuracy": 0.8, "calibration": 0.1}
    assert rm.approve(mock_signal, model_health=health) is True

    # VOLATILE_BREAKOUT tightens drift by 25%: 0.3 * 0.75 = 0.225
    breakout_regime = RegimeInfo(
        label=MarketRegime.VOLATILE_BREAKOUT,
        confidence=0.9,
        transition_score=0.1,
        volatility_index=1.8
    )
    assert rm.approve(mock_signal, model_health=health, regime_info=breakout_regime) is False

def test_risk_manager_regime_adaptive_mean_reversion(mock_config, mock_signal):
    """Verify that RiskManager tightens calibration threshold in MEAN_REVERSION."""
    rm = RiskManager(mock_config, account_balance=10000.0)

    # Borderline calibration: 0.2 < 0.25 (normal)
    health = {"drift": 0.1, "accuracy": 0.8, "calibration": 0.2}
    assert rm.approve(mock_signal, model_health=health) is True

    # MEAN_REVERSION tightens calibration by 40%: 0.25 * 0.6 = 0.15
    mr_regime = RegimeInfo(
        label=MarketRegime.MEAN_REVERSION,
        confidence=0.9,
        transition_score=0.1,
        volatility_index=1.0
    )
    assert rm.approve(mock_signal, model_health=health, regime_info=mr_regime) is False

def test_risk_manager_circuit_breaker_config(mock_config, mock_signal):
    """Verify that RiskManager uses max_drawdown from config."""
    mock_config.max_drawdown = 0.05
    rm = RiskManager(mock_config, account_balance=10000.0)

    # 3% drawdown - should be OK
    rm.update_equity(9700.0)
    assert rm.approve(mock_signal) is True

    # 6% drawdown - should trigger (limit=5%)
    rm.update_equity(9400.0)
    assert rm.approve(mock_signal) is False
