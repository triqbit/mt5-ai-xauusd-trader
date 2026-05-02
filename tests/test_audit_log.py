
import pytest
from sqlalchemy import create_engine, select
from src.core.audit_log import AuditLogger, AuditCategory, AuditEntry, Base
from src.trading.risk_manager import RiskManager, TradeSignal
from src.core.config import TradingConfig
import os

@pytest.fixture
def db_url():
    url = "sqlite:///:memory:"
    return url

@pytest.fixture
def audit_logger(db_url):
    # Reset singleton for testing
    AuditLogger._instance = None
    logger = AuditLogger(db_url)
    return logger

def test_log_basic(audit_logger):
    audit_logger.log(AuditCategory.CONFIG, "TEST_EVENT", "Test Description", metadata={"foo": "bar"})

    with audit_logger.Session() as session:
        entry = session.query(AuditEntry).first()
        assert entry is not None
        assert entry.category == "CONFIG"
        assert entry.event_type == "TEST_EVENT"
        assert entry.description == "Test Description"
        assert entry.metadata_json == {"foo": "bar"}

def test_log_risk_decision(audit_logger):
    audit_logger.log_risk_decision("APPROVED", "All filters passed", {"signal_id": 123})

    with audit_logger.Session() as session:
        entry = session.query(AuditEntry).filter_by(category="RISK").first()
        assert entry.event_type == "DECISION"
        assert entry.metadata_json["signal_id"] == 123

def test_risk_manager_integration(audit_logger, db_url):
    cfg = TradingConfig(
        mt5_password="test",
        mt5_server="test",
        database_url=db_url,
        risk_per_trade=0.01,
        max_daily_loss=0.05,
        max_positions=3
    )
    risk = RiskManager(cfg, 10000.0)

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )

    # Mocking _check_circuit_breaker to return True
    risk._check_circuit_breaker = lambda: True

    approved = risk.approve(signal, signal_id=999)

    with audit_logger.Session() as session:
        entry = session.query(AuditEntry).filter_by(category="RISK").first()
        assert entry is not None
        assert entry.metadata_json["signal_id"] == 999
        assert "filters" in entry.metadata_json
        assert entry.metadata_json["filters"]["symbol_allocation"] is True
