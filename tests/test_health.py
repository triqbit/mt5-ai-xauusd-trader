
import pytest
from unittest.mock import MagicMock, patch
from src.core.health import HealthChecker, HealthStatus
from src.core.config import TradingConfig

@pytest.fixture
def mock_cfg():
    cfg = MagicMock(spec=TradingConfig)
    cfg.is_live = False
    cfg.logs_dir = MagicMock()
    cfg.logs_dir.exists.return_value = True
    return cfg

@pytest.fixture
def checker(mock_cfg):
    return HealthChecker(cfg=mock_cfg)

def test_check_liveness(checker):
    status = checker.check_liveness()
    assert status.status == HealthStatus.HEALTHY
    assert "running" in status.message

def test_check_database_not_initialized(checker):
    status = checker.check_database()
    assert status.status == HealthStatus.FAILED
    assert "not initialized" in status.message

def test_check_database_success(checker):
    mock_logger = MagicMock()
    checker.trade_logger = mock_logger

    # Mocking the context manager
    mock_session = mock_logger.Session.return_value.__enter__.return_value

    status = checker.check_database()
    assert status.status == HealthStatus.HEALTHY
    mock_session.execute.assert_called_once()

def test_check_mt5_not_initialized(checker):
    status = checker.check_mt5()
    assert status.status == HealthStatus.FAILED

def test_check_mt5_connected(checker):
    mock_connector = MagicMock()
    mock_connector._is_initialized = True
    checker.connector = mock_connector

    status = checker.check_mt5()
    assert status.status == HealthStatus.HEALTHY

def test_check_models_none_loaded(checker):
    mock_model = MagicMock()
    mock_model._ppo_model = None
    mock_model.lstm_model = None
    checker.model = mock_model

    status = checker.check_models()
    assert status.status == HealthStatus.FAILED

def test_check_models_some_loaded(checker):
    mock_model = MagicMock()
    mock_model._ppo_model = MagicMock()
    mock_model.lstm_model = None
    checker.model = mock_model

    status = checker.check_models()
    assert status.status == HealthStatus.HEALTHY
    assert "PPO" in status.message

@patch("shutil.disk_usage")
def test_check_disk_space(mock_disk_usage, checker):
    # Mock 200MB free
    mock_disk_usage.return_value = MagicMock(free=200 * 1024 * 1024)

    status = checker.check_disk_space()
    assert status.status == HealthStatus.HEALTHY
    assert status.details["free_mb"] == 200

from src.core.health import ComponentStatus

def test_get_full_report(checker):
    checker.check_database = MagicMock(return_value=ComponentStatus(status=HealthStatus.HEALTHY, message="ok"))
    checker.check_mt5 = MagicMock(return_value=ComponentStatus(status=HealthStatus.HEALTHY, message="ok"))
    checker.check_models = MagicMock(return_value=ComponentStatus(status=HealthStatus.HEALTHY, message="ok"))
    checker.check_config = MagicMock(return_value=ComponentStatus(status=HealthStatus.HEALTHY, message="ok"))
    checker.check_disk_space = MagicMock(return_value=ComponentStatus(status=HealthStatus.HEALTHY, message="ok"))

    report = checker.get_full_report()
    assert report.status == HealthStatus.HEALTHY
    assert "liveness" in report.components

def test_startup_gate_fails(checker):
    checker.get_full_report = MagicMock()
    checker.get_full_report.return_value.status = HealthStatus.FAILED

    with pytest.raises(SystemExit) as e:
        checker.run_startup_gate()
    assert e.value.code == 1
