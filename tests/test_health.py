"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_health.py
Unit and integration tests for the health check system.
"""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from src import __version__
from src.core.config import TradingConfig
from src.core.health import (
    ComponentStatus,
    HealthChecker,
    HealthReport,
    HealthStatus,
    get_system_version,
    init_health_checker,
    router,
)


@pytest.fixture
def mock_config():
    cfg = MagicMock(spec=TradingConfig)
    cfg.logs_dir = MagicMock(spec=Path)
    cfg.logs_dir.exists.return_value = True
    cfg.mt5_login = 12345
    cfg.mt5_server = "TestServer"
    cfg.mt5_password = "TestPassword"
    cfg.mode = "demo"
    cfg.symbol = "XAUUSD"
    cfg.database_url = MagicMock(spec=SecretStr)
    cfg.database_url.get_secret_value.return_value = "sqlite:///:memory:"
    cfg.redis_url = MagicMock(spec=SecretStr)
    cfg.redis_url.get_secret_value.return_value = "redis://localhost:6379/0"
    cfg.telegram_token = MagicMock(spec=SecretStr)
    cfg.telegram_token.get_secret_value.return_value = ""
    cfg.risk_per_trade = 0.01
    cfg.max_daily_loss = 0.05
    cfg.max_positions = 3
    cfg.algorithm = "ensemble"
    return cfg

@pytest.fixture
def mock_connector():
    connector = MagicMock()
    connector._is_initialized = True
    connector.use_metaapi = False
    connector.symbol = "XAUUSD"
    return connector

@pytest.fixture
def mock_trade_logger():
    logger = MagicMock()
    # Mocking SQLAlchemy engine connection
    mock_conn = MagicMock()
    logger.engine.connect.return_value.__enter__.return_value = mock_conn
    logger.engine.dialect.do_ping.return_value = True
    return logger

@pytest.fixture
def mock_model():
    model = MagicMock()
    model.ppo_agent = MagicMock()
    model.lstm_model = MagicMock()
    model.dreamer_agent = MagicMock()
    return model

@pytest.fixture
def mock_audit_logger():
    logger = MagicMock()
    logger._initialized = True
    return logger

@pytest.fixture
def health_checker(mock_config, mock_connector, mock_trade_logger, mock_model, mock_audit_logger):
    return HealthChecker(mock_config, mock_connector, mock_trade_logger, mock_model, mock_audit_logger)

def test_check_liveness(health_checker):
    status = health_checker.check_liveness()
    assert status.status == HealthStatus.HEALTHY
    assert "active" in status.message

def test_check_database_success(health_checker, mock_trade_logger):
    status = health_checker.check_database()
    assert status.status == HealthStatus.HEALTHY
    assert "reachable" in status.message
    mock_trade_logger.engine.connect.assert_called_once()

def test_check_database_failure(health_checker, mock_trade_logger):
    mock_trade_logger.engine.connect.side_effect = Exception("DB error")
    status = health_checker.check_database()
    assert status.status == HealthStatus.FAILED
    assert "DB error" in status.message

def test_check_mt5_success(health_checker, mock_connector):
    mock_connector.get_account_info.return_value = {"balance": 1000}
    status = health_checker.check_mt5()
    assert status.status == HealthStatus.HEALTHY
    assert "active" in status.message

def test_check_mt5_not_initialized(health_checker, mock_connector):
    mock_connector._is_initialized = False
    status = health_checker.check_mt5()
    assert status.status == HealthStatus.FAILED
    assert "not initialized" in status.message

def test_check_mt5_no_info(health_checker, mock_connector):
    mock_connector.get_account_info.return_value = {}
    status = health_checker.check_mt5()
    assert status.status == HealthStatus.FAILED
    assert "failed to return account info" in status.message

def test_check_mt5_api_error(health_checker, mock_connector):
    mock_connector.get_account_info.side_effect = Exception("API error")
    status = health_checker.check_mt5()
    assert status.status == HealthStatus.FAILED
    assert "API call failed" in status.message

def test_check_mt5_circuit_breaker_open(health_checker, mock_connector):
    mock_connector.circuit_state = "OPEN"
    status = health_checker.check_mt5()
    assert status.status == HealthStatus.DEGRADED
    assert "circuit breaker is OPEN" in status.message

def test_check_mt5_metaapi_success(health_checker, mock_connector):
    mock_connector.use_metaapi = True
    status = health_checker.check_mt5()
    assert status.status == HealthStatus.HEALTHY
    assert "MetaAPI" in status.message

def test_check_models_success(health_checker):
    status = health_checker.check_models()
    assert status.status == HealthStatus.HEALTHY
    assert "ppo" in status.message.lower()
    assert "lstm" in status.message.lower()
    assert "dreamer" in status.message.lower()


def test_check_models_partial_ensemble(health_checker, mock_model):
    # Ensemble with missing components should be DEGRADED
    mock_model.lstm_model = None
    mock_model.dreamer_agent = None
    status = health_checker.check_models()
    assert status.status == HealthStatus.DEGRADED
    assert "ppo" in status.message.lower()
    assert "Missing" in status.message
    assert "lstm" in status.message.lower()
    assert "dreamer" in status.message.lower()

def test_check_models_failed(health_checker, mock_model):
    mock_model.ppo_agent = None
    mock_model.lstm_model = None
    mock_model.dreamer_agent = None
    mock_model.transformer_model = None
    mock_model.__class__.__name__ = "Mock"
    mock_model.model = None  # Individual wrapper check
    # MagicMock has all attributes by default, so we must explicitly delete predict
    if hasattr(mock_model, "predict"):
        del mock_model.predict
    status = health_checker.check_models()
    assert status.status == HealthStatus.FAILED

def test_check_models_transformer(health_checker, mock_config, mock_model):
    mock_config.algorithm = "transformer"
    mock_model.ppo_agent = None
    mock_model.lstm_model = None
    mock_model.dreamer_agent = None
    mock_model.transformer_model = MagicMock()
    status = health_checker.check_models()
    assert status.status == HealthStatus.HEALTHY
    assert "transformer" in status.message.lower()


def test_check_models_individual_wrapper(health_checker, mock_config, mock_model):
    mock_config.algorithm = "ppo"
    mock_model.ppo_agent = None
    mock_model.lstm_model = None
    mock_model.dreamer_agent = None
    mock_model.model = MagicMock()

    # Using a real class for the wrapper to avoid brittle __class__.__name__ mocking
    class PPOAgentWrapper:
        def __init__(self, model):
            self.model = model

    health_checker.model = PPOAgentWrapper(mock_model.model)

    status = health_checker.check_models()
    assert status.status == HealthStatus.HEALTHY
    assert "ppo" in status.message.lower()


def test_check_models_algorithm_mismatch(health_checker, mock_config, mock_model):
    mock_config.algorithm = "ppo"
    mock_model.ppo_agent = None
    mock_model.lstm_model = MagicMock()
    mock_model.dreamer_agent = None

    status = health_checker.check_models()
    assert status.status == HealthStatus.FAILED
    assert "Algorithm mismatch" in status.message

def test_startup_gate_success(health_checker, mock_audit_logger):
    with patch.object(HealthChecker, 'get_full_report') as mock_report:
        mock_report.return_value = HealthReport(status=HealthStatus.HEALTHY, components={})
        report = health_checker.startup_gate()
        assert isinstance(report, HealthReport)
        mock_audit_logger.log.assert_called_with("system", "startup_gate_success", "All health checks passed")

def test_startup_gate_failed(health_checker, mock_audit_logger):
    with patch.object(HealthChecker, 'get_full_report') as mock_report:
        mock_report.return_value = HealthReport(
            status=HealthStatus.FAILED,
            components={"mt5": ComponentStatus(status=HealthStatus.FAILED, message="Down")}
        )
        with pytest.raises(RuntimeError) as exc:
            health_checker.startup_gate()
        assert "mt5" in str(exc.value)
        # HealthChecker calls log_operator_action if available
        mock_audit_logger.log_operator_action.assert_called_with(
            operator="system",
            action="startup_gate_failure",
            reason=unittest.mock.ANY,
            metadata=unittest.mock.ANY
        )

@patch("src.core.health.ConfigValidator")
def test_check_config_success(mock_validator_class, health_checker):
    mock_validator = mock_validator_class.return_value
    mock_validator.validate.return_value = MagicMock(success=True, errors=[])

    status = health_checker.check_config()
    assert status.status == HealthStatus.HEALTHY
    assert "valid" in status.message

@patch("src.core.health.ConfigValidator")
def test_check_config_failed(mock_validator_class, health_checker):
    mock_validator = mock_validator_class.return_value
    mock_err = MagicMock(critical=True, message="Critical error")
    mock_validator.validate.return_value = MagicMock(success=False, errors=[mock_err])

    status = health_checker.check_config()
    assert status.status == HealthStatus.FAILED
    assert "Critical error" in status.message

@patch("shutil.disk_usage")
def test_check_disk_space_success(mock_disk_usage, health_checker, mock_config):
    mock_disk_usage.return_value = MagicMock(free=500 * 1024 * 1024) # 500 MB

    status = health_checker.check_disk_space()
    assert status.status == HealthStatus.HEALTHY
    assert "500.0MB" in status.message

@patch("shutil.disk_usage")
def test_check_disk_space_failure(mock_disk_usage, health_checker, mock_config):
    mock_disk_usage.return_value = MagicMock(free=10 * 1024 * 1024) # 10 MB

    status = health_checker.check_disk_space(min_mb=100)
    assert status.status == HealthStatus.FAILED
    assert "Low disk" in status.message

def test_check_database_fallback(health_checker, mock_trade_logger):
    # Mock do_ping to raise AttributeError to trigger SELECT 1 fallback
    mock_trade_logger.engine.dialect.do_ping.side_effect = AttributeError("No do_ping")

    status = health_checker.check_database()
    assert status.status == HealthStatus.HEALTHY
    assert "reachable" in status.message
    # Verification of SQL execution is implicit as it didn't raise exception

def test_check_mt5_metaapi_active_success(health_checker, mock_connector):
    mock_connector.use_metaapi = True
    mock_connector.get_account_info.return_value = {"balance": 1000}

    status = health_checker.check_mt5()
    assert status.status == HealthStatus.HEALTHY
    assert "(via MetaAPI)" in status.message

def test_get_full_report(health_checker, mock_config):
    with patch.object(HealthChecker, 'check_config') as mock_conf:
        mock_conf.return_value = ComponentStatus(status=HealthStatus.HEALTHY, message="OK")
        with patch.object(HealthChecker, 'check_disk_space') as mock_disk:
            mock_disk.return_value = ComponentStatus(status=HealthStatus.HEALTHY, message="OK")
            with patch.object(HealthChecker, 'check_system_resources') as mock_sys:
                mock_sys.return_value = ComponentStatus(status=HealthStatus.HEALTHY, message="OK")
                with patch.object(HealthChecker, 'check_redis') as mock_redis:
                    mock_redis.return_value = ComponentStatus(status=HealthStatus.HEALTHY, message="OK")
                    with patch.object(HealthChecker, 'check_audit_log') as mock_audit:
                        mock_audit.return_value = ComponentStatus(status=HealthStatus.HEALTHY, message="OK")

                        report = health_checker.get_full_report()
                        assert isinstance(report, HealthReport)
                        assert report.status == HealthStatus.HEALTHY
                        assert report.version == __version__
                        assert report.environment == mock_config.mode
                        assert "liveness" in report.components
                        assert "database" in report.components
                        assert "redis" in report.components
                        assert "audit_log" in report.components

# --- FastAPI Endpoint Tests ---

@pytest.fixture
def client(mock_config, mock_connector, mock_trade_logger, mock_model, mock_audit_logger):
    app = FastAPI()
    app.include_router(router)
    init_health_checker(mock_config, mock_connector, mock_trade_logger, mock_model, mock_audit_logger)
    return TestClient(app)

def test_api_liveness(client):
    response = client.get("/health/liveness")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_api_readiness_success(client):
    with patch("src.core.health.HealthChecker.check_config") as mock_conf:
        mock_conf.return_value = ComponentStatus(status=HealthStatus.HEALTHY, message="OK")
        with patch("src.core.health.HealthChecker.check_disk_space") as mock_disk:
            mock_disk.return_value = ComponentStatus(status=HealthStatus.HEALTHY, message="OK")
            with patch("src.core.health.HealthChecker.check_redis") as mock_redis:
                mock_redis.return_value = ComponentStatus(status=HealthStatus.HEALTHY, message="OK")
                with patch("src.core.health.HealthChecker.check_audit_log") as mock_audit:
                    mock_audit.return_value = ComponentStatus(status=HealthStatus.HEALTHY, message="OK")

                    response = client.get("/health/readiness")
                    assert response.status_code == 200
                    assert response.json()["status"] == "healthy"

def test_api_readiness_failure(client):
    with patch("src.core.health.HealthChecker.check_mt5") as mock_mt5:
        mock_mt5.return_value = ComponentStatus(status=HealthStatus.FAILED, message="Down")
        with patch("src.core.health.HealthChecker.check_disk_space") as mock_disk:
            mock_disk.return_value = ComponentStatus(status=HealthStatus.HEALTHY, message="OK")
            with patch("src.core.health.HealthChecker.check_config") as mock_conf:
                mock_conf.return_value = ComponentStatus(status=HealthStatus.HEALTHY, message="OK")

                response = client.get("/health/readiness")
        assert response.status_code == 503
        assert response.json()["detail"]["status"] == "failed"

def test_get_system_version():
    version = get_system_version()
    assert isinstance(version, str)
    assert version != ""
