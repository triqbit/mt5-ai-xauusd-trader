"""
Tests for Jules02 risk hardening and drift monitoring enhancements.
Verifies the 8-layer safety cascade, consecutive loss blocking, and model calibration alerts.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import date
import pandas as pd
import numpy as np
from src.trading.risk_manager import RiskManager, DailyStats
from src.trading.audited_risk_manager import AuditedRiskManager
from src.core.schemas import TradeSignal
from src.models.regime_detector import MarketRegime, RegimeInfo
from src.core.config import TradingConfig
from src.core.monitor import Monitor

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
    cfg.telegram_token = MagicMock()
    cfg.telegram_token.get_secret_value.return_value = ""
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

def test_risk_manager_consecutive_losses(mock_config, mock_signal):
    """Verify that RiskManager blocks trades after max consecutive losses."""
    rm = RiskManager(mock_config, account_balance=10000.0)

    # 1. First 2 losses - should still approve
    rm.record_pnl(-100.0)
    rm.record_pnl(-100.0)
    assert rm.daily.consecutive_losses == 2
    assert rm.approve(mock_signal) is True

    # 2. Third loss (hit limit) - should reject
    rm.record_pnl(-100.0)
    assert rm.daily.consecutive_losses == 3
    assert rm.approve(mock_signal) is False

    # 3. Reset on profit
    rm.record_pnl(50.0)
    assert rm.daily.consecutive_losses == 0
    assert rm.approve(mock_signal) is True

def test_risk_manager_model_health(mock_config, mock_signal):
    """Verify that RiskManager blocks trades based on model health metrics."""
    rm = RiskManager(mock_config, account_balance=10000.0)

    # 1. Healthy model
    health = {"drift": 0.1, "accuracy": 0.8, "calibration": 0.05}
    assert rm.approve(mock_signal, model_health=health) is True

    # 2. High drift
    health = {"drift": 0.4, "accuracy": 0.8, "calibration": 0.05}
    assert rm.approve(mock_signal, model_health=health) is False

    # 3. Low accuracy
    health = {"drift": 0.1, "accuracy": 0.4, "calibration": 0.05}
    assert rm.approve(mock_signal, model_health=health) is False

    # 4. High calibration error
    health = {"drift": 0.1, "accuracy": 0.8, "calibration": 0.3}
    assert rm.approve(mock_signal, model_health=health) is False

def test_audited_risk_manager_10_layer_trace(mock_config, mock_signal):
    """Verify that AuditedRiskManager traces all 10 layers."""
    with patch("src.trading.audited_risk_manager.get_audit_logger") as mock_get_audit:
        mock_audit = MagicMock()
        mock_get_audit.return_value = mock_audit

        arm = AuditedRiskManager(mock_config, account_balance=10000.0)

        # Test approval with all 10 layers passing
        health = {"drift": 0.1, "accuracy": 0.8, "calibration": 0.1}
        arm.approve(mock_signal, model_health=health)

        # Verify the decision chain passed to log_risk_decision
        call_args = mock_audit.log_risk_decision.call_args[1]
        decision_chain = call_args["decision_chain"]

        expected_layers = [
            "circuit_breaker", "daily_loss", "max_positions", "symbol_allocation",
            "min_confidence", "risk_reward", "consecutive_losses", "model_health",
            "volatility_breaker", "regime_safety"
        ]
        for layer in expected_layers:
            assert layer in decision_chain
            assert decision_chain[layer] is True

def test_risk_manager_volatility_breaker(mock_config, mock_signal):
    """Verify that RiskManager blocks on extreme volatility."""
    mock_config.volatility_extreme_threshold = 3.0
    rm = RiskManager(mock_config, account_balance=10000.0)

    # 1. Normal volatility
    data = pd.DataFrame({"atr": [1.0] * 100})
    assert rm.approve(mock_signal, market_data=data) is True

    # 2. Extreme volatility (ratio = 4.0 > 3.0)
    data = pd.DataFrame({"atr": [1.0] * 99 + [4.0]})
    assert rm.approve(mock_signal, market_data=data) is False

def test_risk_manager_regime_safety(mock_config, mock_signal):
    """Verify that RiskManager enforces regime-specific confidence floors."""
    rm = RiskManager(mock_config, account_balance=10000.0)
    mock_config.min_confidence = 0.55

    # 1. News Shock (requires 0.80)
    regime = RegimeInfo(label=MarketRegime.NEWS_SHOCK, confidence=1.0, transition_score=0.0, volatility_index=1.0)

    # Signal with 0.70 confidence should fail in News Shock
    mock_signal = mock_signal.model_copy(update={"confidence": 0.70})
    assert rm.approve(mock_signal, regime_info=regime) is False

    # Signal with 0.85 confidence should pass
    mock_signal = mock_signal.model_copy(update={"confidence": 0.85})
    assert rm.approve(mock_signal, regime_info=regime) is True

    # 2. Trending (requires 0.55)
    regime = RegimeInfo(label=MarketRegime.TRENDING, confidence=1.0, transition_score=0.0, volatility_index=1.0)
    mock_signal = mock_signal.model_copy(update={"confidence": 0.60})
    assert rm.approve(mock_signal, regime_info=regime) is True

def test_risk_manager_position_sizing_multipliers(mock_config):
    """Verify that position sizing applies confidence and volatility multipliers."""
    mock_config.min_lot_size = 0.01
    mock_config.risk_per_trade = 0.01
    mock_config.max_position_size_pct = 100.0 # Disable cap for testing sizing logic
    mock_config.min_confidence = 0.55
    mock_config.volatility_high_threshold = 1.5
    mock_config.volatility_very_high_threshold = 2.0
    mock_config.volatility_extreme_threshold = 3.0

    rm = RiskManager(mock_config, account_balance=10000.0)

    # Win rate=0.5, RR=2 (avg_win=20, avg_loss=10) -> Kelly = (0.5*20 - 0.5*10)/20 = 0.25
    # Risk capital = 10000 * 0.01 = 100
    # Lots = (100 * 0.25) / (10 * 1) = 2.5 lots

    # 1. Standard (100% size)
    data = pd.DataFrame({"atr": [1.0] * 100, "close": [1.0] * 100})
    lots = rm.size_position("XAUUSD", 0.5, 20.0, 10.0, confidence=0.7, market_data=data)
    assert lots == 2.5

    # 2. Medium confidence (50% size)
    lots = rm.size_position("XAUUSD", 0.5, 20.0, 10.0, confidence=0.6, market_data=data)
    assert lots == 1.25

    # 3. High Volatility (75% size)
    data_high_vol = pd.DataFrame({"atr": [1.0] * 99 + [1.6], "close": [1.0] * 100})
    lots = rm.size_position("XAUUSD", 0.5, 20.0, 10.0, confidence=0.7, market_data=data_high_vol)
    assert lots == 1.88 # 2.5 * 0.75 = 1.875 -> 1.88 rounded

    # 4. Combined Medium Conf + High Vol (50% * 75% = 37.5%)
    lots = rm.size_position("XAUUSD", 0.5, 20.0, 10.0, confidence=0.6, market_data=data_high_vol)
    # 2.5 * 0.5 * 0.75 = 0.9375 -> 0.94
    assert lots == 0.94

def test_monitor_calibration_alert(mock_config):
    """Verify that Monitor alerts on high calibration error."""
    with patch("src.core.monitor.Monitor.send_message") as mock_send:
        monitor = Monitor(mock_config)

        # 1. Healthy calibration
        monitor.log_model_performance(accuracy=0.8, drift_score=0.1, calibration_error=0.1)
        mock_send.assert_not_called()

        # 2. Unhealthy calibration
        monitor.log_model_performance(accuracy=0.8, drift_score=0.1, calibration_error=0.3)
        assert mock_send.call_count == 1
        assert "Calibration Error Detected" in mock_send.call_args[0][0]
