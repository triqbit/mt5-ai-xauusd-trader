
from unittest.mock import MagicMock, patch

import pytest

from src.core.exceptions import CircuitBreakerError, MT5DataError
from src.trading.mt5_connector import MT5Connector


@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.mode = "demo"
    cfg.symbol = "XAUUSD"
    cfg.mt5_path = ""
    cfg.mt5_login = 12345
    cfg.mt5_password.get_secret_value.return_value = "pass"
    cfg.mt5_server = "server"
    cfg.metaapi_token = None
    return cfg

@patch("src.trading.mt5_connector.mt5")
@patch("src.trading.mt5_connector.MT5_AVAILABLE", True)
def test_get_account_info_resilience(mock_mt5, mock_config):
    connector = MT5Connector(mock_config)
    connector._is_initialized = True

    # Simulate 2 failures then 1 success
    mock_acc = MagicMock()
    mock_acc._asdict.return_value = {"balance": 1000.0}

    mock_mt5.account_info.side_effect = [None, None, mock_acc]
    mock_mt5.last_error.return_value = (10001, "Failed")
    mock_mt5.initialize.return_value = True

    # Override initialize to set state
    def mock_init():
        connector._is_initialized = True
        return True

    with patch.object(connector, 'initialize', side_effect=mock_init):
        info = connector.get_account_info()
        assert info["balance"] == 1000.0
        assert mock_mt5.account_info.call_count == 3

@patch("src.trading.mt5_connector.mt5")
@patch("src.trading.mt5_connector.MT5_AVAILABLE", True)
def test_get_positions_resilience(mock_mt5, mock_config):
    connector = MT5Connector(mock_config)
    connector._is_initialized = True

    # Simulate 2 failures then 1 success
    pos1 = MagicMock()
    pos1._asdict.return_value = {"ticket": 1}

    mock_mt5.positions_get.side_effect = [None, None, (pos1,)]
    mock_mt5.last_error.return_value = (10001, "Failed")
    mock_mt5.initialize.return_value = True

    def mock_init():
        connector._is_initialized = True
        return True

    with patch.object(connector, 'initialize', side_effect=mock_init):
        positions = connector.get_positions()
        assert len(positions) == 1
        assert positions[0]["ticket"] == 1
        assert mock_mt5.positions_get.call_count == 3

@patch("src.trading.mt5_connector.mt5")
@patch("src.trading.mt5_connector.MT5_AVAILABLE", True)
def test_get_account_balance_failure_propagation(mock_mt5, mock_config):
    connector = MT5Connector(mock_config)
    connector._is_initialized = True

    # All attempts fail
    mock_mt5.account_info.return_value = None
    mock_mt5.last_error.return_value = (10001, "Permanent failure")
    mock_mt5.initialize.return_value = True

    with pytest.raises(MT5DataError):
        connector.get_account_balance()

@patch("src.trading.mt5_connector.mt5")
@patch("src.trading.mt5_connector.MT5_AVAILABLE", True)
def test_circuit_breaker_tripping_on_account_info(mock_mt5, mock_config):
    # Lower threshold for faster test
    connector = MT5Connector(mock_config)
    connector.breaker.failure_threshold = 2
    connector._is_initialized = True

    mock_mt5.account_info.return_value = None
    mock_mt5.last_error.return_value = (10001, "Failed")
    mock_mt5.initialize.return_value = False # Make initialize fail too

    # with_retry will do 3 retries (total 4 attempts)
    # Circuit breaker should trip after 2 failures.
    # But wait, with_retry wraps the whole breaker call?
    # Let's check MT5Connector implementation:
    # @with_retry(...)
    # def get_account_info(self):
    #     return self.breaker(self._get_account_info_logic)()

    # with_retry catches exceptions and sleeps then retries.
    # The breaker wrapper is INSIDE with_retry.
    # 1st attempt: breaker calls logic, logic fails, breaker records failure, raises MT5DataError.
    # with_retry catches, retries.
    # 2nd attempt: breaker calls logic, logic fails, breaker records failure, trips (OPEN), raises MT5DataError.
    # with_retry catches, retries.
    # 3rd attempt: breaker sees OPEN, raises CircuitBreakerError.
    # with_retry does NOT catch CircuitBreakerError (it only catches MT5DataError, MT5ConnectionError).
    # So CircuitBreakerError should propagate.

    with pytest.raises(CircuitBreakerError):
        connector.get_account_info()

    assert connector.circuit_state == "OPEN"

@patch("src.trading.mt5_connector.mt5")
@patch("src.trading.mt5_connector.MT5_AVAILABLE", True)
def test_get_terminal_status_resilience(mock_mt5, mock_config):
    connector = MT5Connector(mock_config)
    connector._is_initialized = True

    mock_info = MagicMock()
    mock_info._asdict.return_value = {"trade_allowed": True}

    mock_mt5.terminal_info.side_effect = [None, mock_info]
    mock_mt5.last_error.return_value = (10001, "Failed")
    mock_mt5.initialize.return_value = True

    def mock_init():
        connector._is_initialized = True
        return True

    with patch.object(connector, 'initialize', side_effect=mock_init):
        status = connector.get_terminal_status()
        assert status["algo_trading"] is True
        assert mock_mt5.terminal_info.call_count == 2

@patch("src.trading.mt5_connector.mt5")
@patch("src.trading.mt5_connector.MT5_AVAILABLE", True)
def test_get_symbol_properties_resilience(mock_mt5, mock_config):
    connector = MT5Connector(mock_config)
    connector._is_initialized = True

    mock_symbol = MagicMock()
    mock_symbol.name = "XAUUSD"
    mock_symbol.trade_mode = 0 # SYMBOL_TRADE_MODE_FULL
    mock_symbol.spread = 10
    mock_symbol.digits = 3
    mock_symbol.point = 0.001
    mock_symbol.trade_contract_size = 100

    mock_mt5.symbol_info.side_effect = [None, mock_symbol]
    mock_mt5.last_error.return_value = (10001, "Failed")
    mock_mt5.initialize.return_value = True
    mock_mt5.SYMBOL_TRADE_MODE_DISABLED = 1

    def mock_init():
        connector._is_initialized = True
        return True

    with patch.object(connector, 'initialize', side_effect=mock_init):
        props = connector.get_symbol_properties("XAUUSD")
        assert props["name"] == "XAUUSD"
        assert mock_mt5.symbol_info.call_count == 2
