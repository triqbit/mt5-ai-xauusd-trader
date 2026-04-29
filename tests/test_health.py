"""
Tests for HealthChecker class.
"""
import pytest
from unittest.mock import MagicMock, patch
from src.core.health import HealthChecker, HealthStatus
from src.core.config import TradingConfig
from pathlib import Path

@pytest.fixture
def config():
    cfg = MagicMock(spec=TradingConfig)
    cfg.mode = "demo"
    cfg.model_path = Path("models/trained/ensemble_latest.pt")
    return cfg

@pytest.fixture
def health_checker(config):
    return HealthChecker(config)

def test_check_mt5_healthy(health_checker):
    connector = MagicMock()
    connector.initialize.return_value = True
    connector.get_account_info.return_value = {"login": 12345, "server": "Demo"}

    report = health_checker.check_mt5(connector)
    assert report.status == HealthStatus.HEALTHY
    assert "Connected" in report.message

def test_check_mt5_failed(health_checker):
    connector = MagicMock()
    connector.initialize.return_value = False

    report = health_checker.check_mt5(connector)
    assert report.status == HealthStatus.FAILED

def test_check_database_healthy(health_checker):
    logger_db = MagicMock()
    # Mocking context manager
    session = MagicMock()
    logger_db.Session.return_value.__enter__.return_value = session

    report = health_checker.check_database(logger_db)
    assert report.status == HealthStatus.HEALTHY

def test_check_database_failed(health_checker):
    logger_db = MagicMock()
    logger_db.Session.side_effect = Exception("DB Error")

    report = health_checker.check_database(logger_db)
    assert report.status == HealthStatus.FAILED

def test_check_models_healthy(health_checker, config):
    with patch.object(Path, "exists", return_value=True):
        report = health_checker.check_models()
        assert report.status == HealthStatus.HEALTHY

def test_check_models_failed(health_checker, config):
    with patch.object(Path, "exists", return_value=False):
        report = health_checker.check_models()
        assert report.status == HealthStatus.FAILED

def test_run_startup_gate_success(health_checker):
    health_checker.get_full_report = MagicMock()
    report = MagicMock()
    report.components = {
        "mt5": MagicMock(status=HealthStatus.HEALTHY),
        "database": MagicMock(status=HealthStatus.HEALTHY),
        "models": MagicMock(status=HealthStatus.HEALTHY),
        "disk": MagicMock(status=HealthStatus.HEALTHY)
    }
    report.overall_status = HealthStatus.HEALTHY
    health_checker.get_full_report.return_value = report

    assert health_checker.run_startup_gate(MagicMock(), MagicMock()) is True

def test_run_startup_gate_fail_live(health_checker, config):
    config.mode = "live"
    health_checker.get_full_report = MagicMock()
    report = MagicMock()
    report.components = {
        "mt5": MagicMock(status=HealthStatus.FAILED, message="Fail"),
        "database": MagicMock(status=HealthStatus.HEALTHY),
        "models": MagicMock(status=HealthStatus.HEALTHY),
        "disk": MagicMock(status=HealthStatus.HEALTHY)
    }
    report.overall_status = HealthStatus.FAILED
    health_checker.get_full_report.return_value = report

    with pytest.raises(SystemExit) as excinfo:
        health_checker.run_startup_gate(MagicMock(), MagicMock())
    assert excinfo.value.code == 1
