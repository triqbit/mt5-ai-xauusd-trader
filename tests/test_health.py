"""
Tests for Health Check System.
"""
import pytest
from unittest.mock import MagicMock, patch, ANY
from pathlib import Path
from src.core.health import HealthCheckSystem, HealthStatus, HealthReport
from src.core.config import TradingConfig

@pytest.fixture
def mock_config():
    config = MagicMock(spec=TradingConfig)
    config.is_live = False
    config.logs_dir = Path("/tmp/logs")
    return config

@pytest.fixture
def mock_connector():
    connector = MagicMock()
    connector._is_initialized = True
    return connector

@pytest.fixture
def mock_trade_logger():
    logger = MagicMock()
    # Mocking the context manager for Session
    session_mock = MagicMock()
    logger.Session.return_value.__enter__.return_value = session_mock
    return logger

@pytest.fixture
def mock_model():
    model = MagicMock()
    model._ppo_model = MagicMock()
    model.lstm_model = MagicMock()
    return model

class TestHealthCheckSystem:
    def test_check_liveness(self, mock_config):
        hcs = HealthCheckSystem(mock_config)
        status = hcs.check_liveness()
        assert status.status == HealthStatus.HEALTHY
        assert status.message == "Application is running"

    def test_check_config_demo(self, mock_config):
        hcs = HealthCheckSystem(mock_config)
        status = hcs.check_config()
        assert status.status == HealthStatus.HEALTHY

    @patch("os.getenv")
    def test_check_config_live_fail(self, mock_getenv, mock_config):
        mock_config.is_live = True
        mock_getenv.return_value = "false"
        hcs = HealthCheckSystem(mock_config)
        status = hcs.check_config()
        assert status.status == HealthStatus.FAILED
        assert "CONFIRM_LIVE_TRADING not set" in status.message

    def test_check_database_success(self, mock_config, mock_trade_logger):
        hcs = HealthCheckSystem(mock_config, trade_logger=mock_trade_logger)
        status = hcs.check_database()
        assert status.status == HealthStatus.HEALTHY
        mock_trade_logger.Session.return_value.__enter__.return_value.execute.assert_called_once_with(ANY)

    def test_check_database_fail(self, mock_config, mock_trade_logger):
        mock_trade_logger.Session.return_value.__enter__.return_value.execute.side_effect = Exception("DB Error")
        hcs = HealthCheckSystem(mock_config, trade_logger=mock_trade_logger)
        status = hcs.check_database()
        assert status.status == HealthStatus.FAILED
        assert "DB Error" in status.message

    def test_check_mt5_success(self, mock_config, mock_connector):
        hcs = HealthCheckSystem(mock_config, connector=mock_connector)
        status = hcs.check_mt5()
        assert status.status == HealthStatus.HEALTHY

    def test_check_mt5_fail(self, mock_config, mock_connector):
        mock_connector._is_initialized = False
        hcs = HealthCheckSystem(mock_config, connector=mock_connector)
        status = hcs.check_mt5()
        assert status.status == HealthStatus.FAILED

    def test_check_models_success(self, mock_config, mock_model):
        hcs = HealthCheckSystem(mock_config, model=mock_model)
        status = hcs.check_models()
        assert status.status == HealthStatus.HEALTHY
        assert "PPO" in status.message
        assert "LSTM" in status.message

    def test_check_models_fail(self, mock_config, mock_model):
        mock_model._ppo_model = None
        mock_model.lstm_model = None
        hcs = HealthCheckSystem(mock_config, model=mock_model)
        status = hcs.check_models()
        assert status.status == HealthStatus.FAILED

    @patch("shutil.disk_usage")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    def test_check_disk_space_healthy(self, mock_mkdir, mock_exists, mock_disk_usage, mock_config):
        mock_exists.return_value = True
        mock_disk_usage.return_value = (1000, 100, 10 * (2**30)) # 10GB free
        hcs = HealthCheckSystem(mock_config)
        status = hcs.check_disk_space()
        assert status.status == HealthStatus.HEALTHY
        assert "10.00 GB free" in status.message

    @patch("shutil.disk_usage")
    @patch("pathlib.Path.exists")
    def test_check_disk_space_failed(self, mock_exists, mock_disk_usage, mock_config):
        mock_exists.return_value = True
        mock_disk_usage.return_value = (1000, 900, 0.1 * (2**30)) # 100MB free
        hcs = HealthCheckSystem(mock_config)
        status = hcs.check_disk_space()
        assert status.status == HealthStatus.FAILED
        assert "Low disk space" in status.message

    def test_get_readiness_report_healthy(self, mock_config, mock_connector, mock_trade_logger, mock_model):
        with patch("shutil.disk_usage") as mock_disk:
            mock_disk.return_value = (1000, 100, 10 * (2**30))
            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True
                hcs = HealthCheckSystem(mock_config, mock_connector, mock_trade_logger, mock_model)
                report = hcs.get_readiness_report()
                assert report.status == HealthStatus.HEALTHY
                assert len(report.components) == 6
