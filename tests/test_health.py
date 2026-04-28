"""
Unit tests for the Health Check system.
tests/test_health.py
"""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from src.core.health import HealthChecker, HealthReport

@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.database_url = "sqlite:///:memory:"
    cfg.model_path = Path("models/trained/ensemble_latest.pt")
    cfg.logs_dir = Path("logs")
    return cfg

@pytest.fixture
def mock_connector():
    return MagicMock()

def test_check_database_success(mock_config, mock_connector):
    checker = HealthChecker(mock_config, mock_connector)
    assert checker.check_database() is True

def test_check_database_failure(mock_config, mock_connector):
    # Forcing a failure by mocking create_engine to raise an exception
    with patch("src.core.health.create_engine", side_effect=Exception("DB Error")):
        checker = HealthChecker(mock_config, mock_connector)
        assert checker.check_database() is False

def test_check_mt5_success(mock_config, mock_connector):
    mock_connector.connect.return_value = True
    checker = HealthChecker(mock_config, mock_connector)
    assert checker.check_mt5() is True

def test_check_mt5_failure(mock_config, mock_connector):
    mock_connector.connect.return_value = False
    checker = HealthChecker(mock_config, mock_connector)
    assert checker.check_mt5() is False

def test_check_model_exists(mock_config, mock_connector):
    with patch.object(Path, "exists", return_value=True):
        checker = HealthChecker(mock_config, mock_connector)
        assert checker.check_model() is True

def test_check_model_missing(mock_config, mock_connector):
    with patch.object(Path, "exists", return_value=False):
        checker = HealthChecker(mock_config, mock_connector)
        assert checker.check_model() is False

def test_check_logs_writeable(mock_config, mock_connector, tmp_path):
    mock_config.logs_dir = tmp_path / "logs"
    checker = HealthChecker(mock_config, mock_connector)
    assert checker.check_logs() is True
    assert (tmp_path / "logs").exists()

def test_run_all_healthy(mock_config, mock_connector):
    checker = HealthChecker(mock_config, mock_connector)
    checker.check_database = MagicMock(return_value=True)
    checker.check_mt5 = MagicMock(return_value=True)
    checker.check_model = MagicMock(return_value=True)
    checker.check_logs = MagicMock(return_value=True)

    report = checker.run_all()
    assert report.status == "healthy"
    assert all(report.checks.values())

def test_run_all_degraded(mock_config, mock_connector):
    mock_config.mode = "backtest"
    checker = HealthChecker(mock_config, mock_connector)
    checker.check_database = MagicMock(return_value=True)
    checker.check_mt5 = MagicMock(return_value=False)
    checker.check_model = MagicMock(return_value=True)
    checker.check_logs = MagicMock(return_value=True)

    report = checker.run_all()
    assert report.status == "degraded"
    assert report.checks["mt5"] is False
    assert report.checks["database"] is True

def test_run_all_mt5_failed_live(mock_config, mock_connector):
    mock_config.mode = "live"
    checker = HealthChecker(mock_config, mock_connector)
    checker.check_database = MagicMock(return_value=True)
    checker.check_mt5 = MagicMock(return_value=False)
    checker.check_model = MagicMock(return_value=True)
    checker.check_logs = MagicMock(return_value=True)

    report = checker.run_all()
    assert report.status == "failed"
    assert report.checks["mt5"] is False

def test_run_all_failed(mock_config, mock_connector):
    mock_config.mode = "demo"
    checker = HealthChecker(mock_config, mock_connector)
    checker.check_database = MagicMock(return_value=False)
    checker.check_mt5 = MagicMock(return_value=False)
    checker.check_model = MagicMock(return_value=True)
    checker.check_logs = MagicMock(return_value=True)

    report = checker.run_all()
    assert report.status == "failed"
    assert report.checks["database"] is False
