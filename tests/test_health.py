"""
Tests for the Health Monitoring module.
"""
from unittest.mock import MagicMock, patch
from pathlib import Path
import pytest
from src.core.health import HealthCheck, HealthStatus, run_health_gate
from src.core.config import TradingConfig

@pytest.fixture
def mock_config():
    config = MagicMock(spec=TradingConfig)
    config.database_url = "sqlite:///:memory:"
    config.model_path = Path("models/trained/ensemble_latest.pt")
    config.logs_dir = Path("logs")
    config.symbol = "XAUUSD"
    return config

@pytest.fixture
def mock_connector():
    connector = MagicMock()
    connector._is_initialized = True
    connector.get_tick.return_value = {"bid": 2000.0, "ask": 2001.0}
    return connector

class TestHealthCheck:
    def test_check_disk_space(self, mock_config):
        checker = HealthCheck(mock_config)
        with patch("shutil.disk_usage") as mock_usage:
            # Mock 10GB free
            mock_usage.return_value = (100*1024**3, 90*1024**3, 10*1024**3)
            health = checker.check_disk_space(min_gb=1.0)
            assert health.status == HealthStatus.HEALTHY

            # Mock 0.5GB free
            mock_usage.return_value = (100*1024**3, 99.5*1024**3, 0.5*1024**3)
            health = checker.check_disk_space(min_gb=1.0)
            assert health.status == HealthStatus.FAILED

    def test_check_database_success(self, mock_config):
        checker = HealthCheck(mock_config)
        # sqlite :memory: should always succeed
        health = checker.check_database()
        assert health.status == HealthStatus.HEALTHY

    def test_check_database_failure(self, mock_config):
        mock_config.database_url = "postgresql://invalid:5432/db"
        checker = HealthCheck(mock_config)
        health = checker.check_database()
        assert health.status == HealthStatus.FAILED

    def test_check_mt5_healthy(self, mock_config, mock_connector):
        checker = HealthCheck(mock_config, mock_connector)
        health = checker.check_mt5()
        assert health.status == HealthStatus.HEALTHY

    def test_check_mt5_no_data(self, mock_config, mock_connector):
        mock_connector.get_tick.return_value = {"bid": 0.0, "ask": 0.0}
        checker = HealthCheck(mock_config, mock_connector)
        health = checker.check_mt5()
        assert health.status == HealthStatus.DEGRADED

    def test_check_mt5_not_initialized(self, mock_config, mock_connector):
        mock_connector._is_initialized = False
        checker = HealthCheck(mock_config, mock_connector)
        health = checker.check_mt5()
        assert health.status == HealthStatus.FAILED

    def test_check_models_found(self, mock_config):
        checker = HealthCheck(mock_config)
        with patch("pathlib.Path.exists") as mock_exists, \
             patch("pathlib.Path.stat") as mock_stat:
            mock_exists.return_value = True
            mock_stat.return_value.st_size = 1024
            health = checker.check_models()
            assert health.status == HealthStatus.HEALTHY

    def test_check_models_missing(self, mock_config):
        checker = HealthCheck(mock_config)
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False
            health = checker.check_models()
            assert health.status == HealthStatus.FAILED

    def test_run_all_aggregated(self, mock_config, mock_connector):
        checker = HealthCheck(mock_config, mock_connector)
        from src.core.health import ComponentHealth
        with patch.object(checker, "check_disk_space") as m_disk, \
             patch.object(checker, "check_database") as m_db, \
             patch.object(checker, "check_mt5") as m_mt5, \
             patch.object(checker, "check_models") as m_models:

            m_disk.return_value = ComponentHealth(status=HealthStatus.HEALTHY, message="ok")
            m_db.return_value = ComponentHealth(status=HealthStatus.HEALTHY, message="ok")
            m_mt5.return_value = ComponentHealth(status=HealthStatus.HEALTHY, message="ok")
            m_models.return_value = ComponentHealth(status=HealthStatus.HEALTHY, message="ok")

            report = checker.run_all()
            assert report.overall_status == HealthStatus.HEALTHY

            m_mt5.return_value = ComponentHealth(status=HealthStatus.DEGRADED, message="degraded")
            report = checker.run_all()
            assert report.overall_status == HealthStatus.DEGRADED

            m_db.return_value = ComponentHealth(status=HealthStatus.FAILED, message="failed")
            report = checker.run_all()
            assert report.overall_status == HealthStatus.FAILED

def test_run_health_gate(mock_config, mock_connector):
    with patch("src.core.health.HealthCheck.run_all") as mock_run_all:
        mock_run_all.return_value.overall_status = HealthStatus.HEALTHY
        assert run_health_gate(mock_config, mock_connector) is True

        mock_run_all.return_value.overall_status = HealthStatus.DEGRADED
        assert run_health_gate(mock_config, mock_connector) is True

        mock_run_all.return_value.overall_status = HealthStatus.FAILED
        assert run_health_gate(mock_config, mock_connector) is False
