"""
Unit tests for HealthGate.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.core.config import TradingConfig
from src.core.health import HealthGate


@pytest.fixture
def mock_config():
    config = MagicMock(spec=TradingConfig)
    config.mt5_password = "password"
    config.mt5_server = "server"
    config.database_url = "sqlite:///test.db"
    return config


def test_health_gate_success(mock_config):
    with (
        patch("socket.create_connection"),
        patch("psutil.virtual_memory") as mock_mem,
        patch("psutil.cpu_percent", return_value=5.0),
    ):
        mock_mem.return_value.percent = 50.0

        gate = HealthGate(mock_config)
        assert gate.run_all_checks() is True
        assert gate.report["environment_vars"] is True
        assert gate.report["internet_connectivity"] is True
        assert gate.report["resource_availability"] is True


def test_health_gate_missing_env(mock_config):
    mock_config.mt5_password = ""

    with (
        patch("socket.create_connection"),
        patch("psutil.virtual_memory") as mock_mem,
        patch("psutil.cpu_percent", return_value=5.0),
    ):
        mock_mem.return_value.percent = 50.0

        gate = HealthGate(mock_config)
        assert gate.run_all_checks() is False
        assert gate.report["environment_vars"] is False


def test_health_gate_no_internet(mock_config):
    with (
        patch("socket.create_connection", side_effect=OSError),
        patch("psutil.virtual_memory") as mock_mem,
        patch("psutil.cpu_percent", return_value=5.0),
    ):
        mock_mem.return_value.percent = 50.0

        gate = HealthGate(mock_config)
        assert gate.run_all_checks() is False
        assert gate.report["internet_connectivity"] is False


def test_health_gate_low_resources(mock_config):
    with (
        patch("socket.create_connection"),
        patch("psutil.virtual_memory") as mock_mem,
        patch("psutil.cpu_percent", return_value=95.0),
    ):
        mock_mem.return_value.percent = 99.0

        gate = HealthGate(mock_config)
        assert gate.run_all_checks() is False
        assert gate.report["resource_availability"] is False
