
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from sqlalchemy import select
from src.core.audit_log import AuditLogger, AuditEntry
from src.trading.risk_manager import RiskManager, TradeSignal
from src.trading.execution_filter import ExecutionFilter, ExecutionDecision
from src.core.config import TradingConfig

@pytest.fixture
def audit_logger():
    # Reset singleton before test
    AuditLogger._instance = None
    AuditLogger._initialized = False
    # Use in-memory SQLite for testing
    logger = AuditLogger(db_url="sqlite:///:memory:")
    yield logger
    # Reset singleton after test
    AuditLogger._instance = None
    AuditLogger._initialized = False

def test_audit_logger_structured_metadata(audit_logger):
    metadata = {"key": "value", "nested": {"a": 1}}
    entry_id = audit_logger.log(
        actor="test_actor",
        action="test_action",
        details="test details",
        metadata=metadata
    )

    with audit_logger.Session() as session:
        entry = session.scalar(select(AuditEntry).where(AuditEntry.id == entry_id))
        assert entry.metadata_json == metadata

def test_risk_manager_audit_trail(audit_logger, mocker):
    # Manually create config to avoid env-var requirements
    config = TradingConfig(
        mt5_password="test_password",
        mt5_server="test_server",
        mt5_login=12345
    )
    rm = RiskManager(config, account_balance=10000.0)

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ppo",
        confidence=0.8
    )

    # Mock checks to control results
    mocker.patch.object(rm, "_check_circuit_breaker", return_value=True)
    mocker.patch.object(rm, "_check_daily_loss", return_value=True)
    mocker.patch.object(rm, "_check_max_positions", return_value=True)
    mocker.patch.object(rm, "_check_symbol_allocation", return_value=True)
    mocker.patch.object(rm, "_check_minimum_confidence", return_value=True)
    mocker.patch.object(rm, "_check_risk_reward", return_value=True)

    approved = rm.approve(signal, signal_id=123)
    assert approved is True

    with audit_logger.Session() as session:
        entry = session.scalar(
            select(AuditEntry)
            .where(AuditEntry.actor == "risk_manager")
            .order_by(AuditEntry.id.desc())
            .limit(1)
        )
        assert entry.metadata_json["signal_id"] == 123
        assert entry.metadata_json["passed"] is True
        assert entry.metadata_json["layers"]["circuit_breaker"] is True

def test_execution_filter_detailed_results():
    ef = ExecutionFilter()

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ppo",
        confidence=0.8
    )

    # Create trending data to satisfy trend angle check
    data = {
        "close": [1900.0 + i for i in range(200)],
        "high": [1905.0 + i for i in range(200)],
        "low": [1895.0 + i for i in range(200)],
        "base_M5_atr": [10.0] * 200,
        "base_M5_ema_8": [1990.0] * 200,
        "base_M5_ema_21": [1980.0] * 200,
        "base_M5_ema_50": [1970.0] * 200,
        "base_M5_ema_200": [1960.0] * 200,
        "base_M5_rsi": [60.0] * 200,
    }
    df = pd.DataFrame(data)

    # We also need to ensure that some indicators are recalculated correctly if not present as expected
    # but here we provide them.

    decision = ef.validate(signal, df, current_drawdown=0.02)

    assert isinstance(decision, ExecutionDecision)
    assert decision.is_approved is True
    assert "atr_volatility" in decision.layer_results
    assert decision.layer_results["atr_volatility"] is True
    assert decision.layer_results["trend_angle"] is True
    assert decision.layer_results["ema_sequence"] is True
