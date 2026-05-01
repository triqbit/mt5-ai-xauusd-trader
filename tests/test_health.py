"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_health.py
Unit and integration tests for the health check system.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

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
    cfg.database_url = "sqlite:///:memory:"
    cfg.logs_dir = Path("/tmp")
    return cfg


@pytest.fixture
def mock_connector():
    conn = MagicMock()
    conn._is_initialized = True
    return conn


@pytest.fixture
def mock_trade_logger():
    tl = MagicMock()
    tl.engine = MagicMock()
    return tl


@pytest.fixture
def mock_model():
    return MagicMock()


@pytest.fixture
def health_checker(mock_config, mock_connector, mock_trade_logger, mock_model):
    return HealthChecker(mock_config, mock_connector, mock_trade_logger, mock_model)


def test_check_liveness(health_checker):
    status = health_checker.check_liveness()
    assert status.status == HealthStatus.HEALTHY
    assert "Application is running" in status.message


def test_check_database_success(health_checker, mock_trade_logger):
    with patch.object(mock_trade_logger.engine, 'connect') as mock_connect:
        status = health_checker.check_database()
        assert status.status == HealthStatus.HEALTHY


def test_check_database_failure(health_checker, mock_trade_logger):
    mock_trade_logger.engine.connect.side_effect = Exception("DB Error")
    status = health_checker.check_database()
    assert status.status == HealthStatus.FAILED
    assert "DB Error" in status.message


def test_check_mt5_success(health_checker):
    status = health_checker.check_mt5()
    assert status.status == HealthStatus.HEALTHY


def test_check_mt5_failure(health_checker, mock_connector):
    mock_connector._is_initialized = False
    status = health_checker.check_mt5()
    assert status.status == HealthStatus.FAILED


def test_check_models_success(health_checker, mock_model):
    mock_model._ppo_model = MagicMock()
    mock_model.lstm_model = MagicMock()
    status = health_checker.check_models()
    assert status.status == HealthStatus.HEALTHY


def test_check_models_partial(health_checker, mock_model):
    mock_model._ppo_model = MagicMock()
    mock_model.lstm_model = None
    status = health_checker.check_models()
    assert status.status == HealthStatus.HEALTHY # One model is enough for HEALTHY as per current logic
    assert "PPO" in status.message


def test_check_models_failed(health_checker, mock_model):
    mock_model._ppo_model = None
    mock_model.lstm_model = None
    status = health_checker.check_models()
    assert status.status == HealthStatus.FAILED


def test_check_config_success(health_checker):
    with patch("src.core.health.ConfigValidator") as mock_val:
        mock_val.return_value.validate.return_value.success = True
        mock_val.return_value.validate.return_value.errors = []
        status = health_checker.check_config()
        assert status.status == HealthStatus.HEALTHY


def test_check_config_failed(health_checker):
    with patch("src.core.health.ConfigValidator") as mock_val:
        mock_val.return_value.validate.return_value.success = False
        mock_error = MagicMock()
        mock_error.critical = True
        mock_error.message = "Critical Error"
        mock_val.return_value.validate.return_value.errors = [mock_error]
        status = health_checker.check_config()
        assert status.status == HealthStatus.FAILED


def test_check_disk_space_success(health_checker):
    with patch("shutil.disk_usage") as mock_usage:
        mock_usage.return_value.free = 1024 * 1024 * 500 # 500MB
        status = health_checker.check_disk_space()
        assert status.status == HealthStatus.HEALTHY


def test_check_disk_space_failure(health_checker):
    with patch("shutil.disk_usage") as mock_usage:
        mock_usage.return_value.free = 1024 * 1024 * 50 # 50MB
        status = health_checker.check_disk_space()
        assert status.status == HealthStatus.FAILED


def test_get_full_report(health_checker):
    with patch.object(HealthChecker, 'check_database') as mock_db,          patch.object(HealthChecker, 'check_mt5') as mock_mt5,          patch.object(HealthChecker, 'check_models') as mock_models,          patch.object(HealthChecker, 'check_config') as mock_conf,          patch.object(HealthChecker, 'check_disk_space') as mock_disk:

        mock_db.return_value = ComponentStatus(status=HealthStatus.HEALTHY, message="OK")
        mock_mt5.return_value = ComponentStatus(status=HealthStatus.HEALTHY, message="OK")
        mock_models.return_value = ComponentStatus(status=HealthStatus.HEALTHY, message="OK")
        mock_conf.return_value = ComponentStatus(status=HealthStatus.HEALTHY, message="OK")
        mock_disk.return_value = ComponentStatus(status=HealthStatus.HEALTHY, message="OK")

        report = health_checker.get_full_report()
        assert isinstance(report, HealthReport)
        assert report.status == HealthStatus.HEALTHY
        assert "liveness" in report.components
        assert "database" in report.components

# --- FastAPI Endpoint Tests ---

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
    with patch.object(HealthChecker, 'get_full_report') as mock_report:
        mock_report.return_value = HealthReport(
            status=HealthStatus.HEALTHY,
            timestamp="2024-01-01T00:00:00Z",
            components={}
        )
        response = client.get("/health/readiness")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

def test_api_readiness_failure(client):
    with patch.object(HealthChecker, 'get_full_report') as mock_report:
        mock_report.return_value = HealthReport(
            status=HealthStatus.FAILED,
            timestamp="2024-01-01T00:00:00Z",
            components={}
        )
        response = client.get("/health/readiness")
        assert response.status_code == 503
