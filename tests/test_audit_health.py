"""
Unit tests for AuditLogger and additional health checks.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.audit_log import AuditEntry, AuditLogger
from src.core.config import TradingConfig
from src.core.health import HealthChecker, HealthStatus


@pytest.fixture
def db_url():
    return "sqlite:///:memory:"

@pytest.fixture
def mock_config():
    cfg = MagicMock(spec=TradingConfig)
    cfg.logs_dir = MagicMock(spec=Path)
    cfg.logs_dir.exists.return_value = True

    mock_redis_url = MagicMock()
    mock_redis_url.get_secret_value.return_value = "redis://localhost:6379/0"
    cfg.redis_url = mock_redis_url
    return cfg

def test_audit_logger_singleton(db_url):
    # Reset singleton for testing
    AuditLogger._instance = None
    AuditLogger._initialized = False

    logger1 = AuditLogger(db_url)
    logger2 = AuditLogger(db_url)
    assert logger1 is logger2
    assert logger1._initialized is True

def test_audit_log_entry(db_url):
    AuditLogger._instance = None
    AuditLogger._initialized = False
    logger = AuditLogger(db_url)

    entry_id = logger.log("test_actor", "test_action", "test_details")
    assert entry_id is not None

    with logger.Session() as session:
        entry = session.get(AuditEntry, entry_id)
        assert entry.actor == "test_actor"
        assert entry.action == "test_action"
        assert entry.details == "test_details"

def test_check_redis_success(mock_config):
    checker = HealthChecker(mock_config)
    with patch("redis.from_url") as mock_redis:
        mock_client = mock_redis.return_value
        mock_client.ping.return_value = True

        status = checker.check_redis()
        assert status.status == HealthStatus.HEALTHY
        assert "reachable" in status.message

def test_check_redis_failure(mock_config):
    checker = HealthChecker(mock_config)
    with patch("redis.from_url") as mock_redis:
        mock_client = mock_redis.return_value
        mock_client.ping.return_value = False

        status = checker.check_redis()
        assert status.status == HealthStatus.DEGRADED
        assert "ping failed" in status.message

def test_check_redis_exception(mock_config):
    checker = HealthChecker(mock_config)
    with patch("redis.from_url") as mock_redis:
        mock_redis.side_effect = Exception("Connection refused")

        status = checker.check_redis()
        assert status.status == HealthStatus.DEGRADED
        assert "Redis unreachable" in status.message

def test_check_audit_log_success(mock_config):
    mock_audit = MagicMock()
    mock_audit._initialized = True
    checker = HealthChecker(mock_config, audit_logger=mock_audit)

    status = checker.check_audit_log()
    assert status.status == HealthStatus.HEALTHY
    assert "active" in status.message

def test_check_audit_log_failure(mock_config):
    mock_audit = MagicMock()
    mock_audit._initialized = False
    checker = HealthChecker(mock_config, audit_logger=mock_audit)

    status = checker.check_audit_log()
    assert status.status == HealthStatus.FAILED
    assert "not properly initialized" in status.message

def test_check_audit_log_none(mock_config):
    checker = HealthChecker(mock_config, audit_logger=None)

    status = checker.check_audit_log()
    assert status.status == HealthStatus.FAILED
    assert "not initialized" in status.message
