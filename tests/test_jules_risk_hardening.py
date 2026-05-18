"""
Tests for Jules02 risk hardening and drift monitoring enhancements.
Verifies the 8-layer safety cascade, consecutive loss blocking, and model calibration alerts.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.core.config import TradingConfig
from src.core.monitor import Monitor
from src.core.schemas import TradeSignal
from src.trading.audited_risk_manager import AuditedRiskManager
from src.trading.risk_manager import RiskManager


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

def test_audited_risk_manager_8_layer_trace(mock_config, mock_signal):
    """Verify that AuditedRiskManager traces all 8 layers."""
    with patch("src.trading.audited_risk_manager.get_audit_logger") as mock_get_audit:
        mock_audit = MagicMock()
        mock_get_audit.return_value = mock_audit

        arm = AuditedRiskManager(mock_config, account_balance=10000.0)

        # Test approval with all 8 layers passing
        health = {"drift": 0.1, "accuracy": 0.8, "calibration": 0.1}
        arm.approve(mock_signal, model_health=health)

        # Verify the decision chain passed to log_risk_decision
        call_args = mock_audit.log_risk_decision.call_args[1]
        decision_chain = call_args["decision_chain"]

        expected_layers = [
            "circuit_breaker", "daily_loss", "max_positions", "symbol_allocation",
            "min_confidence", "risk_reward", "consecutive_losses", "model_health"
        ]
        for layer in expected_layers:
            assert layer in decision_chain
            assert decision_chain[layer] is True

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
