
import pytest
from unittest.mock import MagicMock
from src.trading.risk_manager import RiskManager, TradeSignal, TradingConfig
from src.core.audit_log import AuditLogger

@pytest.fixture
def config():
    cfg = MagicMock(spec=TradingConfig)
    cfg.max_positions = 3
    cfg.risk_per_trade = 0.01
    cfg.max_daily_loss = 0.05
    cfg.confidence_threshold = 0.6
    return cfg

@pytest.fixture
def audit_logger():
    return MagicMock(spec=AuditLogger)

@pytest.fixture
def risk_manager(config, audit_logger):
    return RiskManager(config, account_balance=10000.0, audit_logger=audit_logger)

def test_risk_manager_approve_with_audit(risk_manager, audit_logger):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8
    )

    # Mocking internal checks to ensure they pass
    risk_manager._check_circuit_breaker = MagicMock(return_value=True)
    risk_manager._check_daily_loss = MagicMock(return_value=True)
    risk_manager._check_max_positions = MagicMock(return_value=True)
    risk_manager._check_symbol_allocation = MagicMock(return_value=True)
    risk_manager._check_minimum_confidence = MagicMock(return_value=True)
    risk_manager._check_risk_reward = MagicMock(return_value=True)

    assert risk_manager.approve(signal, signal_id=123) is True

    # Verify audit_logger.log was called
    audit_logger.log.assert_called_once()
    args, kwargs = audit_logger.log.call_args
    assert kwargs['category'] == "RISK"
    assert kwargs['event_type'] == "RISK_APPROVAL"
    assert "decision_chain" in kwargs['details']
    assert kwargs['details']['signal_id'] == 123
    assert len(kwargs['details']['decision_chain']) == 6
    assert all(d['passed'] for d in kwargs['details']['decision_chain'])

def test_risk_manager_reject_with_audit(risk_manager, audit_logger):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.4 # Low confidence
    )

    # Mocking internal checks
    risk_manager._check_circuit_breaker = MagicMock(return_value=True)
    risk_manager._check_daily_loss = MagicMock(return_value=True)
    risk_manager._check_max_positions = MagicMock(return_value=True)
    risk_manager._check_symbol_allocation = MagicMock(return_value=True)
    risk_manager._check_minimum_confidence = MagicMock(return_value=False) # Fail
    risk_manager._check_risk_reward = MagicMock(return_value=True)

    assert risk_manager.approve(signal, signal_id=456) is False

    # Verify audit_logger.log was called
    audit_logger.log.assert_called_once()
    args, kwargs = audit_logger.log.call_args
    assert kwargs['category'] == "RISK"
    assert "Filter failed: min_confidence" in kwargs['reason']
    assert kwargs['details']['signal_id'] == 456

    chain = kwargs['details']['decision_chain']
    assert chain[4]['filter'] == "min_confidence"
    assert chain[4]['passed'] is False
