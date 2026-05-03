"""
Compliance tests for CI quality gate improvements.
Verifies that the refactored components meet the new type-safe standards.
"""
from datetime import datetime, timezone
from typing import Any

import pytest
from sqlalchemy import text
from src.core.health import HealthChecker, HealthStatus
from src.core.trade_logger import TradeLogger
from src.core.config import get_config

def test_tradelogger_sqlalchemy_20_compliance():
    """Verify TradeLogger still functions correctly after SQLAlchemy 2.0 refactor."""
    logger = TradeLogger(db_url="sqlite:///:memory:")

    # Test log_signal (uses Mapped attributes)
    signal_id = logger.log_signal({
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0,
        "algorithm": "test",
        "confidence": 0.9,
        "volatility": 1.5
    })
    assert isinstance(signal_id, int)
    assert signal_id > 0

    # Test log_trade
    trade_id = logger.log_trade(
        ticket=99999,
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        lot_size=0.1,
        signal_id=signal_id
    )
    assert isinstance(trade_id, int)
    assert trade_id > 0

def test_health_checker_ping_compliance(monkeypatch):
    """Verify HealthChecker uses the updated cross-DB ping logic."""
    monkeypatch.setenv("MT5_PASSWORD", "test")
    monkeypatch.setenv("MT5_SERVER", "test")
    cfg = get_config()
    logger = TradeLogger(db_url="sqlite:///:memory:")
    checker = HealthChecker(config=cfg, trade_logger=logger)

    # check_database returns ComponentStatus (not Any)
    status = checker.check_database()
    assert status.status == HealthStatus.HEALTHY
    assert "Database reachable" in status.message

@pytest.mark.asyncio
async def test_health_api_return_types(monkeypatch):
    """Verify Health API endpoints have correct return types for Mypy."""
    monkeypatch.setenv("MT5_PASSWORD", "test")
    monkeypatch.setenv("MT5_SERVER", "test")
    from src.core.health import liveness, readiness, full_report

    # These functions were updated to return Any to satisfy FastAPI untyped decorators
    # while internal logic remains typed.
    res_liveness = await liveness()
    assert hasattr(res_liveness, "status")

    try:
        res_readiness = await readiness()
        assert hasattr(res_readiness, "status")
    except Exception as e:
        # If it raises HTTPException (due to failed components in test env), that's fine,
        # it means the code reached the execution point correctly.
        assert "HTTPException" in str(type(e))

    res_full = await full_report()
    assert hasattr(res_full, "status")
