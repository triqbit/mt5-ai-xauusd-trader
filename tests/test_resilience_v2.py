from unittest.mock import MagicMock, patch

import pytest

from src.core.exceptions import MT5DataError, MT5ExecutionError, TradingError
from src.core.retry import with_retry
from src.core.schemas import TradeSignal
from src.trading.mt5_connector import MT5Connector

# --- Enhanced Retry Tests ---

def test_retry_respects_is_retriable_false():
    class PermanentError(TradingError):
        def __init__(self):
            super().__init__("Permanent", is_retriable=False)

    mock_func = MagicMock(side_effect=PermanentError())

    @with_retry(PermanentError, max_retries=3, initial_delay=0.01, jitter=False)
    def decorated_func():
        return mock_func()

    with pytest.raises(PermanentError):
        decorated_func()

    # Should only call once because is_retriable=False
    assert mock_func.call_count == 1

def test_retry_continues_if_is_retriable_true():
    class TransientError(TradingError):
        def __init__(self):
            super().__init__("Transient", is_retriable=True)

    mock_func = MagicMock(side_effect=[TransientError(), "success"])

    @with_retry(TransientError, max_retries=3, initial_delay=0.01, jitter=False)
    def decorated_func():
        return mock_func()

    assert decorated_func() == "success"
    assert mock_func.call_count == 2

# --- MT5Connector Error Categorization Tests ---

@patch("src.trading.mt5_connector.mt5")
def test_get_rates_permanent_failure(mock_mt5, mk_config):
    connector = MT5Connector(mk_config)
    connector._is_initialized = True

    # RES_E_INVALID_PARAMS (-2) is marked as non-retriable
    mock_mt5.copy_rates_from_pos.return_value = None
    mock_mt5.last_error.return_value = (-2, "Invalid parameters")

    with pytest.raises(MT5DataError) as excinfo:
        connector.get_rates("INVALID", "M5", 10)

    assert excinfo.value.is_retriable is False
    # with_retry should catch it and re-raise immediately
    assert mock_mt5.copy_rates_from_pos.call_count == 1

@patch("src.trading.mt5_connector.mt5")
def test_place_order_permanent_rejection(mock_mt5, mk_config):
    connector = MT5Connector(mk_config)
    connector._is_initialized = True
    connector.use_metaapi = False

    signal = TradeSignal(
        symbol="XAUUSD", direction=1, entry_price=2300.0,
        stop_loss=2290.0, take_profit=2320.0, lot_size=0.1,
        algorithm="ppo", confidence=0.8
    )

    # Mock tick info
    mock_mt5.symbol_info_tick.return_value = MagicMock(ask=2300.0, bid=2299.0)

    # TRADE_RETCODE_NO_MONEY (10019) is marked as non-retriable
    mock_result = MagicMock()
    mock_result.retcode = 10019
    mock_result.comment = "No money"
    mock_mt5.order_send.return_value = mock_result

    with pytest.raises(MT5ExecutionError) as excinfo:
        connector.place_order(signal)

    assert excinfo.value.is_retriable is False
    assert mock_mt5.order_send.call_count == 1

@patch("src.trading.mt5_connector.mt5")
def test_place_order_retriable_rejection(mock_mt5, mk_config):
    connector = MT5Connector(mk_config)
    connector._is_initialized = True
    connector.use_metaapi = False

    signal = TradeSignal(
        symbol="XAUUSD", direction=1, entry_price=2300.0,
        stop_loss=2290.0, take_profit=2320.0, lot_size=0.1,
        algorithm="ppo", confidence=0.8
    )

    mock_mt5.symbol_info_tick.return_value = MagicMock(ask=2300.0, bid=2299.0)

    # TRADE_RETCODE_REQUOTE (10004) is NOT in NON_RETRIABLE_RETCODES
    mock_result_fail = MagicMock(retcode=10004, comment="Requote")
    mock_result_success = MagicMock(retcode=10009, order=123) # TRADE_RETCODE_DONE

    mock_mt5.order_send.side_effect = [mock_result_fail, mock_result_success]
    mock_mt5.TRADE_RETCODE_DONE = 10009

    ticket = connector.place_order(signal)

    assert ticket == 123
    assert mock_mt5.order_send.call_count == 2

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
