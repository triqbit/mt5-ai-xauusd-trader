"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_resilience_hardened.py
Unit tests for retry logic and hardened exception propagation.
Author : triqbit
License: MIT
"""

from unittest.mock import MagicMock, patch

import pytest

from src.core.exceptions import MT5ConnectionError, MT5DataError
from src.core.retry import with_retry
from src.trading.mt5_connector import MT5Connector

# Mocking heavy dependencies to allow tests to run in light environments
with patch.dict(
    "sys.modules",
    {
        "MetaTrader5": MagicMock(),
        "metaapi_cloud_sdk": MagicMock(),
        "torch": MagicMock(),
        "stable_baselines3": MagicMock(),
    },
):

    def test_with_retry_success():
        """Verify that with_retry succeeds if the function returns eventually."""
        mock_func = MagicMock(side_effect=[ValueError("Fail"), ValueError("Fail"), "Success"])

        @with_retry(max_retries=3, base_delay=0.1, exceptions=ValueError)
        def decorated():
            return mock_func()

        result = decorated()
        assert result == "Success"
        assert mock_func.call_count == 3

    def test_with_retry_exhausted():
        """Verify that with_retry raises the exception after max retries."""
        mock_func = MagicMock(side_effect=ValueError("Persistent Fail"))

        @with_retry(max_retries=2, base_delay=0.1, exceptions=ValueError)
        def decorated():
            return mock_func()

        with pytest.raises(ValueError, match="Persistent Fail"):
            decorated()
        assert mock_func.call_count == 3  # Initial + 2 retries

    def test_connector_initialize_raises_on_failure():
        """Verify MT5Connector.initialize raises MT5ConnectionError after retries."""
        config = MagicMock()
        config.mt5_path = None
        config.mt5_login = 123
        config.mt5_password = MagicMock()
        config.mt5_password.get_secret_value.return_value = "pass"
        config.mt5_server = "server"
        config.metaapi_token = None
        config.mode = "demo"

        connector = MT5Connector(config)

        with (
            patch("src.trading.mt5_connector.MT5_AVAILABLE", True),
            patch("src.trading.mt5_connector.mt5.initialize", return_value=False),
            patch("src.trading.mt5_connector.mt5.last_error", return_value=(1, "Connect error")),
            pytest.raises(MT5ConnectionError),
        ):
            # We use a small max_retries in the test by patching the decorator or just letting it run
            # Since initialize is decorated with max_retries=3, it will attempt 4 times
            connector.initialize()

    def test_connector_get_rates_raises_on_failure():
        """Verify MT5Connector.get_rates raises MT5DataError."""
        config = MagicMock()
        connector = MT5Connector(config)
        connector._is_initialized = True
        connector.use_metaapi = False

        with (
            patch("src.trading.mt5_connector.mt5.copy_rates_from_pos", return_value=None),
            patch("src.trading.mt5_connector.mt5.last_error", return_value=(-1, "No rates")),
            pytest.raises(MT5DataError),
        ):
            connector.get_rates("XAUUSD", "M5", 100)
