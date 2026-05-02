"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_health.py
Unit and integration tests for the health check system.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from src.core.config import TradingConfig
from src.core.health import (
    ComponentStatus,
    HealthChecker,
    HealthReport,
    HealthStatus,
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
    cfg.mt5_password = SecretStr("TestPassword")
    cfg.mode = "demo"
    cfg.database_url = SecretStr("sqlite:///:memory:")
    cfg.telegram_token = SecretStr("")
    cfg.risk_per_trade = 0.01
    cfg.max_daily_loss = 0.05
    cfg.max_positions = 3
    return cfg


@pytest.fixture
def mock_connector():
    connector = MagicMock()
    connector._is_initialized = True
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
    model._ppo_model = MagicMock()
    model.lstm_model = MagicMock()
    return model


@pytest.fixture
def health_checker(mock_config, mock_connector, mock_trade_logger, mock_model):
    return HealthChecker(mock_config, mock_connector, mock_trade_logger, mock_model)


def test_check_liveness(health_checker):
    status = health_checker.check_liveness()
    assert status.status == HealthStatus.HEALTHY
    assert "running" in status.message


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


def test_check_mt5_success(health_checker):
    status = health_checker.check_mt5()
    assert status.status == HealthStatus.HEALTHY
    assert "alive" in status.message


def test_check_mt5_failure(health_checker, mock_connector):
    mock_connector._is_initialized = False
    status = health_checker.check_mt5()
    assert status.status == HealthStatus.FAILED
    assert "down" in status.message


def test_check_models_success(health_checker):
    status = health_checker.check_models()
    assert status.status == HealthStatus.HEALTHY
    assert "PPO" in status.message
    assert "LSTM" in status.message


def test_check_models_partial(health_checker, mock_model):
    mock_model.lstm_model = None
    status = health_checker.check_models()
    assert status.status == HealthStatus.HEALTHY
    assert "PPO" in status.message
    assert "LSTM" not in status.message


def test_check_models_failed(health_checker, mock_model):
    mock_model._ppo_model = None
    mock_model.lstm_model = None
    status = health_checker.check_models()
    assert status.status == HealthStatus.FAILED


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
    mock_disk_usage.return_value = MagicMock(free=500 * 1024 * 1024)  # 500 MB

    status = health_checker.check_disk_space()
    assert status.status == HealthStatus.HEALTHY
    assert "500.00MB" in status.message


@patch("shutil.disk_usage")
def test_check_disk_space_failure(mock_disk_usage, health_checker, mock_config):
    mock_disk_usage.return_value = MagicMock(free=10 * 1024 * 1024)  # 10 MB

    status = health_checker.check_disk_space(min_mb=100)
    assert status.status == HealthStatus.FAILED
    assert "Low disk space" in status.message


def test_get_full_report(health_checker):
    with patch.object(HealthChecker, "check_config") as mock_conf:
        mock_conf.return_value = ComponentStatus(status=HealthStatus.HEALTHY, message="OK")
        with patch.object(HealthChecker, "check_disk_space") as mock_disk:
            mock_disk.return_value = ComponentStatus(status=HealthStatus.HEALTHY, message="OK")
            # ConfigValidator uses cfg.mt5_password etc.
            report = health_checker.get_full_report()
            assert isinstance(report, HealthReport)
            assert report.status == HealthStatus.HEALTHY
            assert "liveness" in report.components
            assert "database" in report.components


# --- FastAPI Endpoint Tests ---

from fastapi import FastAPI


@pytest.fixture
def client(mock_config, mock_connector, mock_trade_logger, mock_model):
    app = FastAPI()
    app.include_router(router)
    init_health_checker(mock_config, mock_connector, mock_trade_logger, mock_model)
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
