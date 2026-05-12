from unittest.mock import MagicMock, patch

import pytest

from src.core.exceptions import CircuitBreakerError, MT5ConnectionError, MT5DataError
from src.trading.mt5_connector import MT5Connector


@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.mode = "demo"
    cfg.symbol = "XAUUSD"
    cfg.mt5_password.get_secret_value.return_value = "pass"
    cfg.metaapi_token = None
    return cfg

@patch("src.trading.mt5_connector.mt5")
@patch("src.trading.mt5_connector.MT5_AVAILABLE", True)
def test_circuit_breaker_tripping_full(mock_mt5, mock_config):
    connector = MT5Connector(mock_config)
    connector.breaker.failure_threshold = 3

    mock_mt5.initialize.return_value = False
    mock_mt5.last_error.return_value = (-1, "Failed")

    with patch("src.core.retry.with_retry", lambda *args, **kwargs: lambda f: f):
        connector.initialize = connector.breaker(connector._initialize_logic)

        # Fail 1
        with pytest.raises(MT5ConnectionError):
            connector.initialize()
        assert connector.breaker._failure_count == 1
        assert connector.circuit_state == "CLOSED"

        # Fail 2
        with pytest.raises(MT5ConnectionError):
            connector.initialize()
        assert connector.breaker._failure_count == 2
        assert connector.circuit_state == "CLOSED"

        # Fail 3 -> Trips
        with pytest.raises(MT5ConnectionError):
            connector.initialize()
        assert connector.breaker._failure_count == 3
        assert connector.circuit_state == "OPEN"

        # Fail 4 -> CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            connector.initialize()

@patch("src.trading.mt5_connector.mt5")
@patch("src.trading.mt5_connector.MT5_AVAILABLE", True)
def test_get_rates_trips_breaker_full(mock_mt5, mock_config):
    connector = MT5Connector(mock_config)
    connector.breaker.failure_threshold = 2
    # Ensure _is_initialized is True so it doesn't try to call initialize() which might be wrapped differently
    connector._is_initialized = True

    mock_mt5.copy_rates_from_pos.return_value = None
    mock_mt5.last_error.return_value = (-1, "Connection lost")

    # Bypass initialize() because it sets _is_initialized=True on success,
    # but more importantly, we don't want it to run during this test.
    # Actually, _get_rates_logic calls initialize() if not _is_initialized.
    # In our case it IS initialized, but failing calls set _is_initialized = False.

    # Let's mock initialize to do nothing
    connector.initialize = MagicMock()

    # Manually wrap for test to avoid decorator interference
    connector.get_rates = connector.breaker(connector._get_rates_logic)

    # Fail 1
    with pytest.raises(MT5DataError):
        connector.get_rates("XAUUSD", "M5", 10)
    assert connector.breaker._failure_count == 1

    # Fail 2 -> Trip
    with pytest.raises(MT5DataError):
        connector.get_rates("XAUUSD", "M5", 10)

    assert connector.circuit_state == "OPEN"
