
import pytest
from unittest.mock import MagicMock, patch
from src.trading.risk_manager import RiskManager, TradeSignal, TradingConfig
from src.core.constants import SignalDirection
from datetime import datetime

@pytest.fixture
def mock_config():
    config = MagicMock(spec=TradingConfig)
    config.mt5_login = 12345
    config.mt5_server = "Broker-Server"
    config.mt5_password = MagicMock()
    config.mt5_password.get_secret_value.return_value = "password"
    config.symbol = "XAUUSD"
    config.risk_per_trade = 0.01
    config.max_daily_loss = 0.05
    config.max_positions = 3
    config.confidence_threshold = 0.6
    config.model_drift_threshold = 0.3
    config.model_accuracy_floor = 0.5
    config.model_win_rate_floor = 0.45
    return config

@pytest.fixture
def risk_manager(mock_config):
    return RiskManager(mock_config, account_balance=10000.0)

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

def test_approve_with_high_drift(risk_manager, valid_signal):
    health = {"drift": 0.4, "accuracy": 0.8}
    # Should be rejected because drift 0.4 > threshold 0.3
    assert risk_manager.approve(valid_signal, model_health=health) is False

def test_approve_with_low_accuracy(risk_manager, valid_signal):
    health = {"drift": 0.1, "accuracy": 0.4}
    # Should be rejected because accuracy 0.4 < floor 0.5
    assert risk_manager.approve(valid_signal, model_health=health) is False

def test_approve_with_healthy_model(risk_manager, valid_signal):
    health = {"drift": 0.1, "accuracy": 0.7}
    # Should be approved
    assert risk_manager.approve(valid_signal, model_health=health) is True

def test_approve_no_health_data(risk_manager, valid_signal):
    # Should be approved (fail-safe)
    assert risk_manager.approve(valid_signal, model_health=None) is True

def test_approve_low_historical_win_rate(risk_manager, valid_signal):
    mock_logger = MagicMock()
    # Win rate 0.4 < floor 0.45, with 25 trades
    mock_logger.read_performance_report.return_value = {"win_rate": 0.4, "total_trades": 25}
    risk_manager.trade_logger = mock_logger

    assert risk_manager.approve(valid_signal) is False

def test_approve_low_historical_win_rate_insufficient_data(risk_manager, valid_signal):
    mock_logger = MagicMock()
    # Win rate 0.4 < floor 0.45, but only 10 trades
    mock_logger.read_performance_report.return_value = {"win_rate": 0.4, "total_trades": 10}
    risk_manager.trade_logger = mock_logger

    assert risk_manager.approve(valid_signal) is True

def test_minimum_confidence_from_config(risk_manager, valid_signal):
    risk_manager.cfg.confidence_threshold = 0.8
    valid_signal.confidence = 0.7
    # Rejected because 0.7 < 0.8
    assert risk_manager.approve(valid_signal) is False

    valid_signal.confidence = 0.85
    # Approved
    assert risk_manager.approve(valid_signal) is True
