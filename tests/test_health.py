"""
Tests for HealthChecker.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from src.core.health import HealthChecker, HealthStatus, create_health_app
from src.core.config import TradingConfig
from src.trading.mt5_connector import MT5Connector
from src.core.trade_logger import TradeLogger
from src.models.ensemble import EnsembleModel

@pytest.fixture
def mock_deps():
    config = MagicMock(spec=TradingConfig)
    config.mode = "demo"
    config.logs_dir = MagicMock()
    config.logs_dir.exists.return_value = True
    config.database_url = "sqlite:///trades.db"

    connector = MagicMock(spec=MT5Connector)
    connector._is_initialized = True

    trade_logger = MagicMock()
    # Mocking Session() as a context manager
    session_mock = MagicMock()
    trade_logger.Session.return_value.__enter__.return_value = session_mock

    model = MagicMock(spec=EnsembleModel)
    model._ppo_model = MagicMock()
    model.lstm_model = MagicMock()

    return config, connector, trade_logger, model

def test_health_check_liveness(mock_deps):
    config, _, _, _ = mock_deps
    checker = HealthChecker(config)
    response = checker.check_liveness()
    assert response.status == HealthStatus.HEALTHY
    assert "process" in response.checks

def test_health_check_readiness_healthy(mock_deps):
    config, connector, trade_logger, model = mock_deps

    with patch("src.core.health.ConfigValidator") as MockValidator:
        MockValidator.return_value.validate.return_value = (True, [])
        with patch("shutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(free=10 * 1024**3) # 10GB

            checker = HealthChecker(config, connector, trade_logger, model)
            response = checker.check_readiness()

            assert response.status == HealthStatus.HEALTHY
            assert response.checks["config"]["status"] == "HEALTHY"
            assert response.checks["database"]["status"] == "HEALTHY"
            assert response.checks["mt5"]["status"] == "HEALTHY"
            assert response.checks["models"]["status"] == "HEALTHY"
            assert response.checks["disk_space"]["status"] == "HEALTHY"

def test_health_check_readiness_failed_db(mock_deps):
    config, connector, trade_logger, model = mock_deps
    trade_logger.Session.return_value.__enter__.side_effect = Exception("DB Fail")

    with patch("src.core.health.ConfigValidator") as MockValidator:
        MockValidator.return_value.validate.return_value = (True, [])
        with patch("shutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(free=10 * 1024**3)

            checker = HealthChecker(config, connector, trade_logger, model)
            response = checker.check_readiness()

            assert response.status == HealthStatus.FAILED
            assert response.checks["database"]["status"] == "FAILED"

def test_startup_health_gate_exit(mock_deps):
    config, connector, trade_logger, model = mock_deps

    with patch("src.core.health.ConfigValidator") as MockValidator:
        MockValidator.return_value.validate.return_value = (False, ["Critical Error"])
        checker = HealthChecker(config, connector, trade_logger, model)

        with pytest.raises(SystemExit) as exc:
            checker.run_startup_health_gate()
        assert exc.value.code == 1

def test_health_app_liveness(mock_deps):
    config, _, _, _ = mock_deps
    checker = HealthChecker(config)
    app = create_health_app(checker)

    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.get("/health/liveness")
    assert response.status_code == 200
    assert response.json()["status"] == "HEALTHY"

def test_health_app_readiness_healthy(mock_deps):
    config, connector, trade_logger, model = mock_deps

    with patch("src.core.health.ConfigValidator") as MockValidator:
        MockValidator.return_value.validate.return_value = (True, [])
        with patch("shutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(free=10 * 1024**3)

            checker = HealthChecker(config, connector, trade_logger, model)
            app = create_health_app(checker)

            from fastapi.testclient import TestClient
            client = TestClient(app)
            response = client.get("/health/readiness")
            assert response.status_code == 200
            assert response.json()["status"] == "HEALTHY"

def test_health_app_readiness_failed(mock_deps):
    config, connector, trade_logger, model = mock_deps

    with patch("src.core.health.ConfigValidator") as MockValidator:
        MockValidator.return_value.validate.return_value = (False, ["Config Error"])
        with patch("shutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(free=10 * 1024**3)

            checker = HealthChecker(config, connector, trade_logger, model)
            app = create_health_app(checker)

            from fastapi.testclient import TestClient
            client = TestClient(app)
            response = client.get("/health/readiness")
            assert response.status_code == 503
            assert response.json()["status"] == "FAILED"
