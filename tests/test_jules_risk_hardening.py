
import pytest
from unittest.mock import MagicMock
from datetime import datetime
from src.trading.risk_manager import RiskManager, TradeSignal, DailyStats
from src.trading.audited_risk_manager import AuditedRiskManager
from src.core.config import TradingConfig

@pytest.fixture
def mock_config():
    config = MagicMock(spec=TradingConfig)
    config.risk_per_trade = 0.01
    config.max_daily_loss = 0.05
    config.max_drawdown = 0.15
    config.max_positions = 5
    config.min_confidence = 0.55
    config.max_losing_streak = 3
    config.model_drift_threshold = 0.3
    config.model_accuracy_floor = 0.5
    config.model_calibration_threshold = 0.25
    return config

@pytest.fixture
def risk_manager(mock_config):
    return RiskManager(config=mock_config, account_balance=10000.0)

@pytest.fixture
def audited_risk_manager(mock_config):
    return AuditedRiskManager(config=mock_config, account_balance=10000.0)

@pytest.fixture
def valid_signal():
    return TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.7,
        timestamp=datetime.utcnow()
    )

def test_losing_streak_blocking(risk_manager, valid_signal):
    # Simulate 3 consecutive losses
    risk_manager.record_pnl(-100.0)
    risk_manager.record_pnl(-50.0)
    risk_manager.record_pnl(-20.0)

    assert risk_manager.daily.consecutive_losses == 3
    assert risk_manager.approve(valid_signal) is False

    # Win resets the streak
    risk_manager.record_pnl(10.0)
    assert risk_manager.daily.consecutive_losses == 0
    assert risk_manager.approve(valid_signal) is True

def test_model_health_drift_blocking(risk_manager, valid_signal):
    health = {"drift": 0.4, "accuracy": 0.7, "calibration": 0.1}
    assert risk_manager.approve(valid_signal, model_health=health) is False

def test_model_health_accuracy_blocking(risk_manager, valid_signal):
    health = {"drift": 0.1, "accuracy": 0.4, "calibration": 0.1}
    assert risk_manager.approve(valid_signal, model_health=health) is False

def test_model_health_calibration_blocking(risk_manager, valid_signal):
    health = {"drift": 0.1, "accuracy": 0.7, "calibration": 0.3}
    assert risk_manager.approve(valid_signal, model_health=health) is False

def test_model_health_pass(risk_manager, valid_signal):
    health = {"drift": 0.1, "accuracy": 0.7, "calibration": 0.1}
    assert risk_manager.approve(valid_signal, model_health=health) is True

def test_audited_risk_manager_decision_chain(audited_risk_manager, valid_signal):
    health = {"drift": 0.4, "accuracy": 0.7, "calibration": 0.1}
    # We don't necessarily need to mock the audit logger if it's handled gracefully
    with MagicMock() as mock_audit:
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("src.trading.audited_risk_manager.get_audit_logger", lambda: mock_audit)
            audited_risk_manager.approve(valid_signal, model_health=health)

            # Check if audit was called with the full chain
            mock_audit.log_risk_decision.assert_called_once()
            args, kwargs = mock_audit.log_risk_decision.call_args
            chain = kwargs["decision_chain"]
            assert "losing_streak" in chain
            assert "model_health" in chain
            assert chain["model_health"] is False

def test_config_driven_thresholds(risk_manager, valid_signal):
    # Change threshold in config
    risk_manager.cfg.min_confidence = 0.8
    valid_signal.confidence = 0.75
    assert risk_manager.approve(valid_signal) is False

    valid_signal.confidence = 0.85
    assert risk_manager.approve(valid_signal) is True
