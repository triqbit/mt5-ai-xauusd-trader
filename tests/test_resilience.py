from unittest.mock import MagicMock, patch

import pytest

from src.core.exceptions import MT5ConnectionError
from src.core.retry import with_retry

# --- Retry Decorator Tests ---

def test_retry_success():
    mock_func = MagicMock(return_value="success")

    @with_retry(ValueError, max_retries=3, initial_delay=0.01, jitter=False)
    def decorated_func():
        return mock_func()

    result = decorated_func()
    assert result == "success"
    assert mock_func.call_count == 1

def test_retry_eventual_success():
    mock_func = MagicMock(side_effect=[ValueError("fail"), ValueError("fail"), "success"])

    @with_retry(ValueError, max_retries=3, initial_delay=0.01, jitter=False)
    def decorated_func():
        return mock_func()

    result = decorated_func()
    assert result == "success"
    assert mock_func.call_count == 3

def test_retry_max_retries_exceeded():
    mock_func = MagicMock(side_effect=ValueError("fail"))

    @with_retry(ValueError, max_retries=2, initial_delay=0.01, jitter=False)
    def decorated_func():
        return mock_func()

    with pytest.raises(ValueError, match="fail"):
        decorated_func()

    assert mock_func.call_count == 3  # Initial + 2 retries

# --- MT5Connector Resilience Tests ---

@patch("src.trading.mt5_connector.mt5")
def test_connector_initialize_native_fails_no_fallback(mock_mt5, mk_config):
    from src.trading.mt5_connector import MT5Connector
    connector = MT5Connector(mk_config)

    # Native fails, MetaAPI not available (METAAPI_TOKEN is empty in mk_config)
    with patch("src.trading.mt5_connector.MT5_AVAILABLE", True):
        mock_mt5.initialize.return_value = False
        mock_mt5.last_error.return_value = (1, "error")

        with pytest.raises(MT5ConnectionError, match="All MT5 connection paths failed"):
            connector.initialize()

        # retried 3 times (max_retries=3)
        assert mock_mt5.initialize.call_count == 4

@patch("src.trading.mt5_connector.mt5")
def test_connector_initialize_dual_path_success(mock_mt5, mk_config):
    from src.trading.mt5_connector import MT5Connector

    # Mock MetaAPI to avoid event loop issues
    with patch("src.trading.mt5_connector.MetaApi") as mock_metaapi:
        # Properly mock the async methods
        mock_api_instance = mock_metaapi.return_value
        mock_acc_api = mock_api_instance.metatrader_account_api

        async def mock_async_none(*args, **kwargs): return None
        async def mock_async_acc(*args, **kwargs):
            m_acc = MagicMock()
            m_acc.wait_connected.side_effect = mock_async_none
            m_acc.get_rpc_connection.return_value.connect.side_effect = mock_async_none
            m_acc.get_rpc_connection.return_value.wait_synchronized.side_effect = mock_async_none
            return m_acc

        mock_acc_api.get_account.side_effect = mock_async_acc

        mk_config.metaapi_token.get_secret_value.return_value = "fake-token"
        mk_config.metaapi_account_id = "fake-acc-id"
        connector = MT5Connector(mk_config)

        with patch("src.trading.mt5_connector.MT5_AVAILABLE", True), \
             patch("src.trading.mt5_connector.METAAPI_AVAILABLE", True):

            # Native fails
            mock_mt5.initialize.return_value = False
            mock_mt5.last_error.return_value = (1, "error")

            # MetaAPI succeeds
            res = connector.initialize()

            assert res is True
            assert connector.use_metaapi is True
            assert mock_mt5.initialize.call_count == 1
            mock_metaapi.assert_called_once()

@patch("src.trading.mt5_connector.mt5")
def test_connector_get_rates_retry(mock_mt5, mk_config):
    from src.trading.mt5_connector import MT5Connector
    connector = MT5Connector(mk_config)
    connector._is_initialized = True

    # Simulate transient rates failure
    mock_mt5.copy_rates_from_pos.side_effect = [None, None, [{"time": 1, "close": 1.0}]]
    mock_mt5.last_error.return_value = (2, "data error")

    df = connector.get_rates("XAUUSD", "M5", 10)

    assert not df.empty
    assert mock_mt5.copy_rates_from_pos.call_count == 3

# Fixture for TradingConfig
@pytest.fixture
def mk_config():
    cfg = MagicMock()
    cfg.mt5_path = ""
    cfg.mt5_login = 123
    cfg.mt5_password.get_secret_value.return_value = "pass"
    cfg.mt5_server = "server"
    cfg.metaapi_token.get_secret_value.return_value = ""
    cfg.mode = "demo"
    return cfg
