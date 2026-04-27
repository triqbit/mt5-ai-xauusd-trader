import pytest
from unittest.mock import MagicMock, patch
from src.trading.risk_manager import RiskManager

def test_telegram_alert_on_circuit_breaker(test_config, db_logger, monitor, mock_telegram):
    # Setup RiskManager with a low balance to trigger circuit breaker
    # initial balance 10000, current balance 8000 -> 20% drawdown (>15% limit)
    risk = RiskManager(test_config, account_balance=8000.0, logger_db=db_logger, monitor=monitor)
    risk.peak_equity = 10000.0

    # Trigger circuit breaker check
    passed = risk._check_circuit_breaker()

    assert passed is False
    # Verify telegram message was sent
    mock_telegram.send_message.assert_called()
    args, kwargs = mock_telegram.send_message.call_args
    assert "CRITICAL: Circuit Breaker Triggered!" in kwargs['text']
    assert kwargs['chat_id'] == test_config.telegram_chat_id

def test_confidence_degradation_alert(monitor, mock_telegram, test_config):
    # Threshold is 0.6 in test_config
    monitor.check_confidence_degradation(0.4)

    mock_telegram.send_message.assert_called()
    args, kwargs = mock_telegram.send_message.call_args
    assert "WARNING: Model Confidence Degradation" in kwargs['text']
    assert "0.400" in kwargs['text']

def test_daily_summary_alert(risk_manager_with_monitor, mock_telegram):
    # We need a risk manager with a monitor
    risk_manager_with_monitor.record_pnl(500.0)
    risk_manager_with_monitor.reset_daily()

    mock_telegram.send_message.assert_called()
    args, kwargs = mock_telegram.send_message.call_args
    assert "Daily Summary" in kwargs['text']
    assert "500.00" in kwargs['text']

@pytest.fixture
def risk_manager_with_monitor(test_config, db_logger, monitor):
    return RiskManager(test_config, account_balance=10000.0, logger_db=db_logger, monitor=monitor)
