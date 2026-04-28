"""
Tests for the health check system.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.health import ComponentStatus, HealthChecker, HealthStatus, startup_health_gate


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.model_path = Path("models/trained/ensemble_latest.pt")
    config.logs_dir = Path("logs")
    config.mt5_password = "password"
    config.mt5_server = "server"
    return config


@pytest.fixture
def mock_connector():
    connector = MagicMock()
    connector._is_initialized = True
    connector.get_account_info.return_value = {"login": 12345}
    return connector


@pytest.fixture
def mock_trade_logger():
    logger = MagicMock()
    # Mocking sqlalchemy engine and connection
    mock_conn = MagicMock()
    logger.engine.connect.return_value.__enter__.return_value = mock_conn
    return logger


def test_health_checker_liveness(mock_config):
    checker = HealthChecker(mock_config)
    liveness = checker.get_liveness()
    assert liveness.status == HealthStatus.HEALTHY
    assert "Application is responsive" in liveness.message


def test_check_database_success(mock_config, mock_trade_logger):
    checker = HealthChecker(mock_config)
    status = checker.check_database(mock_trade_logger)
    assert status.status == HealthStatus.HEALTHY
    assert "Database reachable" in status.message


def test_check_database_failure(mock_config, mock_trade_logger):
    mock_trade_logger.engine.connect.side_effect = Exception("DB error")
    checker = HealthChecker(mock_config)
    status = checker.check_database(mock_trade_logger)
    assert status.status == HealthStatus.FAILED
    assert "Database unreachable" in status.message


def test_check_mt5_success(mock_config, mock_connector):
    checker = HealthChecker(mock_config)
    status = checker.check_mt5(mock_connector)
    assert status.status == HealthStatus.HEALTHY
    assert "MT5 connection alive" in status.message
    assert status.details == {"login": "12345"}


def test_check_mt5_not_initialized(mock_config, mock_connector):
    mock_connector._is_initialized = False
    checker = HealthChecker(mock_config)
    status = checker.check_mt5(mock_connector)
    assert status.status == HealthStatus.FAILED
    assert "MT5 connector not initialized" in status.message


def test_check_models_success(mock_config):
    with patch.object(Path, "exists", return_value=True):
        checker = HealthChecker(mock_config)
        status = checker.check_models()
        assert status.status == HealthStatus.HEALTHY


def test_check_models_failure(mock_config):
    with patch.object(Path, "exists", return_value=False):
        checker = HealthChecker(mock_config)
        status = checker.check_models()
        assert status.status == HealthStatus.FAILED


def test_check_config_success(mock_config):
    checker = HealthChecker(mock_config)
    status = checker.check_config()
    assert status.status == HealthStatus.HEALTHY


def test_check_config_failure(mock_config):
    mock_config.mt5_password = ""
    checker = HealthChecker(mock_config)
    status = checker.check_config()
    assert status.status == HealthStatus.FAILED
    assert "MT5_PASSWORD" in status.message


def test_check_disk_space_success(mock_config):
    with patch("shutil.disk_usage", return_value=(0, 0, 2 * 1024**3)):
        with patch.object(Path, "exists", return_value=True):
            checker = HealthChecker(mock_config)
            status = checker.check_disk_space()
            assert status.status == HealthStatus.HEALTHY
            assert "2.00 GB free" in status.message


def test_check_disk_space_degraded(mock_config):
    with patch("shutil.disk_usage", return_value=(0, 0, 0.5 * 1024**3)):
        with patch.object(Path, "exists", return_value=True):
            checker = HealthChecker(mock_config)
            status = checker.check_disk_space()
            assert status.status == HealthStatus.DEGRADED
            assert "0.50 GB free" in status.message


def test_get_readiness_overall_healthy(mock_config, mock_connector, mock_trade_logger):
    checker = HealthChecker(mock_config)
    with patch.object(
        checker,
        "check_database",
        return_value=ComponentStatus(status=HealthStatus.HEALTHY, message="OK"),
    ):
        with patch.object(
            checker,
            "check_mt5",
            return_value=ComponentStatus(status=HealthStatus.HEALTHY, message="OK"),
        ):
            with patch.object(
                checker,
                "check_models",
                return_value=ComponentStatus(status=HealthStatus.HEALTHY, message="OK"),
            ):
                with patch.object(
                    checker,
                    "check_config",
                    return_value=ComponentStatus(status=HealthStatus.HEALTHY, message="OK"),
                ):
                    with patch.object(
                        checker,
                        "check_disk_space",
                        return_value=ComponentStatus(status=HealthStatus.HEALTHY, message="OK"),
                    ):
                        report = checker.get_readiness(mock_connector, mock_trade_logger)
                        assert report.status == HealthStatus.HEALTHY


def test_get_readiness_overall_failed(mock_config, mock_connector, mock_trade_logger):
    checker = HealthChecker(mock_config)
    with patch.object(
        checker,
        "check_database",
        return_value=ComponentStatus(status=HealthStatus.FAILED, message="Fail"),
    ):
        # We need to mock other methods too because get_readiness calls them all
        with patch.object(
            checker, "check_mt5", return_value=ComponentStatus(status=HealthStatus.HEALTHY, message="OK")
        ):
            with patch.object(
                checker,
                "check_models",
                return_value=ComponentStatus(status=HealthStatus.HEALTHY, message="OK"),
            ):
                with patch.object(
                    checker,
                    "check_config",
                    return_value=ComponentStatus(status=HealthStatus.HEALTHY, message="OK"),
                ):
                    with patch.object(
                        checker,
                        "check_disk_space",
                        return_value=ComponentStatus(status=HealthStatus.HEALTHY, message="OK"),
                    ):
                        report = checker.get_readiness(mock_connector, mock_trade_logger)
                        assert report.status == HealthStatus.FAILED


def test_startup_health_gate_success(mock_config, mock_connector, mock_trade_logger):
    with patch("src.core.health.HealthChecker.get_readiness") as mock_readiness:
        mock_readiness.return_value = MagicMock(status=HealthStatus.HEALTHY)
        # Should not raise
        startup_health_gate(mock_config, mock_connector, mock_trade_logger)


def test_startup_health_gate_failure(mock_config, mock_connector, mock_trade_logger):
    with patch("src.core.health.HealthChecker.get_readiness") as mock_readiness:
        mock_readiness.return_value = MagicMock(
            status=HealthStatus.FAILED,
            overall_message="Critical health failure",
            components={"database": MagicMock(status=HealthStatus.FAILED, message="DB down")},
        )
        with pytest.raises(RuntimeError, match="Startup health check failed"):
            startup_health_gate(mock_config, mock_connector, mock_trade_logger)
