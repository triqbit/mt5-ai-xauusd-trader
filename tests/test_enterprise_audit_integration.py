"""
MT5 AI/ML Trading Bot - Enterprise Integration Test
tests/test_enterprise_audit_integration.py

Verifies the Enterprise Decision & Audit Flow:
Model Inference -> Execution Filter -> Audited Risk Manager -> Audit Persistence

Protects: Cross-module blocking reason propagation and audit traceability.
"""

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import select

# Standardize mocks for use across all tests and imports
mock_torch = MagicMock()


class MockTensor:
    pass


mock_torch.Tensor = MockTensor
mock_sb3 = MagicMock()
mock_talib = MagicMock()

with patch.dict(
    "sys.modules",
    {
        "torch": mock_torch,
        "torch.nn": mock_torch.nn,
        "stable_baselines3": mock_sb3,
        "talib": mock_talib,
    },
):
    from src.core.audit_log import AuditEntry, AuditLogger
    from src.core.config import get_config
    from src.core.constants import SignalDirection
    from src.trading.audited_risk_manager import AuditedRiskManager
    from src.trading.execution_filter import ExecutionFilter
    from src.trading.risk_manager import TradeSignal


@pytest.fixture(autouse=True)
def reset_audit_logger():
    """Reset the AuditLogger singleton before each test."""
    AuditLogger._instance = None
    AuditLogger._initialized = False


@pytest.fixture
def audit_logger():
    """Provide a fresh in-memory AuditLogger."""
    return AuditLogger(db_url="sqlite:///:memory:")


@pytest.fixture
def mock_cfg():
    with patch.dict(
        os.environ,
        {
            "MT5_PASSWORD": "test_password",
            "MT5_SERVER": "test_server",
            "TELEGRAM_TOKEN": "123:abc",
            "TELEGRAM_CHAT_ID": "123456",
            "MODE": "demo",
            "MIN_CONFIDENCE": "0.7",
        },
    ):
        get_config.cache_clear()
        return get_config()


def test_enterprise_audit_flow_double_rejection(mock_cfg, audit_logger):
    """
    Scenario: Signal is generated, but fails both Execution Filter and Risk Manager.
    Verifies that BOTH components log their detailed traces to the audit DB.
    """
    # 1. Setup Signal
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY.value,
        entry_price=2300.0,
        stop_loss=2295.0,
        take_profit=2315.0,  # (R:R = 15/5 = 3.0)
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.85,
    )

    # 2. Setup Market Data that fails Trend Angle (Moving Average is going down)
    df = pd.DataFrame(
        {
            "close": np.linspace(2310, 2300, 100),  # Downtrend
            "high": np.linspace(2315, 2305, 100),
            "low": np.linspace(2305, 2295, 100),
            "base_M5_ema_21": np.linspace(2310, 2300, 100),  # EMA 21 following downtrend
        }
    )

    # 3. Execution Filter Validation (Should fail TREND_ANGLE)
    execution_filter = ExecutionFilter(config=mock_cfg)
    # Use a fixed Wednesday timestamp to avoid SESSION_CLOSED during CI runs on weekends
    fixed_timestamp = datetime(2024, 5, 22, 12, 0, tzinfo=timezone.utc)
    ef_decision = execution_filter.validate(
        signal, df, current_drawdown=0.0, timestamp=fixed_timestamp
    )

    assert ef_decision.is_approved is False
    assert ef_decision.blocked_by == "TREND_ANGLE"

    # Log EF decision manually as main.py would
    audit_logger.log_execution_decision(
        symbol=signal.symbol,
        direction=signal.direction,
        trace=ef_decision.trace,
        is_approved=ef_decision.is_approved,
    )

    # 4. Audited Risk Manager Validation (Should fail)
    risk_manager = AuditedRiskManager(mock_cfg, account_balance=10000.0)
    # Force rejection by mocking one of the risk layers
    with patch.object(risk_manager, "_check_risk_reward", return_value=False):
        # AuditedRiskManager.approve calls audit_logger.log_risk_decision internally
        risk_approved = risk_manager.approve(signal)
        assert risk_approved is False

    # 5. Verify Audit Persistence
    with audit_logger.Session() as session:
        # Check Execution Decision Entry
        ef_entry = session.scalars(
            select(AuditEntry)
            .where(AuditEntry.action == "execution_decision")
            .order_by(AuditEntry.id.desc())
        ).first()
        assert ef_entry.metadata_json["is_approved"] is False
        assert ef_entry.metadata_json["trace"]["trend_angle"]["passed"] is False
        assert ef_entry.metadata_json["symbol"] == "XAUUSD"

        # Check Risk Decision Entry
        risk_entry = session.scalars(
            select(AuditEntry)
            .where(AuditEntry.action == "risk_decision")
            .order_by(AuditEntry.id.desc())
        ).first()
        assert risk_entry.metadata_json["passed"] is False
        assert risk_entry.metadata_json["decision_chain"]["risk_reward"] is False
        assert risk_entry.metadata_json["decision_chain"]["circuit_breaker"] is True


def test_enterprise_audit_flow_execution_pass_risk_fail(mock_cfg, audit_logger):
    """
    Scenario: Execution filter passes but Risk Manager rejects.
    Verifies that the audit trail correctly distinguishes where the trade was blocked.
    """
    # 1. Setup Signal
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY.value,
        entry_price=2300.0,
        stop_loss=2299.0,
        take_profit=2302.0,  # (R:R = 2/1 = 2.0)
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.85,
    )

    # 2. Market data that passes (Uptrend)
    df = pd.DataFrame(
        {
            "close": np.linspace(2290, 2300, 100),
            "high": np.linspace(2295, 2305, 100),
            "low": np.linspace(2285, 2295, 100),
            "base_M5_ema_21": np.linspace(2290, 2300, 100),
            "base_M5_ema_8": np.linspace(2295, 2305, 100),
            "base_M5_ema_50": np.linspace(2280, 2290, 100),
            "base_M5_ema_200": np.linspace(2270, 2280, 100),
            "base_M5_rsi": [60.0] * 100,
            "base_M5_atr": [1.0] * 100,
        }
    )

    # 3. Execution Filter Validation (Should PASS)
    execution_filter = ExecutionFilter(config=mock_cfg)
    # Use a fixed Wednesday timestamp to avoid SESSION_CLOSED during CI runs on weekends
    fixed_timestamp = datetime(2024, 5, 22, 12, 0, tzinfo=timezone.utc)
    ef_decision = execution_filter.validate(
        signal, df, current_drawdown=0.0, timestamp=fixed_timestamp
    )

    assert ef_decision.is_approved is True

    audit_logger.log_execution_decision(
        symbol=signal.symbol,
        direction=signal.direction,
        trace=ef_decision.trace,
        is_approved=ef_decision.is_approved,
    )

    # 4. Audited Risk Manager Validation (Should FAIL)
    risk_manager = AuditedRiskManager(mock_cfg, account_balance=10000.0)
    with patch.object(risk_manager, "_check_risk_reward", return_value=False):
        risk_approved = risk_manager.approve(signal)
        assert risk_approved is False

    # 5. Verify Audit Persistence
    with audit_logger.Session() as session:
        # Check Execution Decision (Passed)
        ef_entry = session.scalars(
            select(AuditEntry)
            .where(AuditEntry.action == "execution_decision")
            .order_by(AuditEntry.id.desc())
        ).first()
        assert ef_entry.metadata_json["is_approved"] is True

        # Check Risk Decision (Failed)
        risk_entry = session.scalars(
            select(AuditEntry)
            .where(AuditEntry.action == "risk_decision")
            .order_by(AuditEntry.id.desc())
        ).first()
        assert risk_entry.metadata_json["passed"] is False
        assert risk_entry.metadata_json["decision_chain"]["risk_reward"] is False
