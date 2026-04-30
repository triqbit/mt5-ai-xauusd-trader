import pytest
import sys
from unittest.mock import MagicMock, patch

# Mock MetaTrader5 before importing MT5Connector
mock_mt5 = MagicMock()
sys.modules['MetaTrader5'] = mock_mt5

from src.trading.mt5_connector import MT5Connector
from src.core.config import TradingConfig
from src.core.exceptions import MT5ConnectionError, MarketDataError, OrderExecutionError
from src.trading.risk_manager import TradeSignal
import pandas as pd

@pytest.fixture
def mock_config():
    config = MagicMock(spec=TradingConfig)
    config.mode = "demo"
    config.mt5_path = "path"
    config.mt5_login = 12345
    config.mt5_password = "password"
    config.mt5_server = "server"
    config.metaapi_token = ""
    return config

@pytest.fixture
def connector(mock_config):
    with patch('src.trading.mt5_connector.MT5_AVAILABLE', True):
        return MT5Connector(mock_config)

def test_initialize_retry_success(connector):
    """Test that initialize retries and eventually succeeds."""
    # Reset mock and set side effect
    mock_mt5.initialize.reset_mock()
    mock_mt5.initialize.side_effect = [False, False, True]

    result = connector.initialize(max_retries=3)

    assert result is True
    assert mock_mt5.initialize.call_count == 3

def test_initialize_retry_failure(connector):
    """Test that initialize fails after max retries."""
    mock_mt5.initialize.reset_mock()
    mock_mt5.initialize.side_effect = None
    mock_mt5.initialize.return_value = False

    result = connector.initialize(max_retries=3)

    assert result is False
    assert mock_mt5.initialize.call_count == 3

def test_get_rates_uninitialized(connector):
    """Test that get_rates raises MT5ConnectionError if not initialized."""
    with pytest.raises(MT5ConnectionError):
        connector.get_rates("XAUUSD", "M5", 100)

def test_get_rates_retry_success(connector):
    """Test that get_rates retries and succeeds."""
    connector._is_initialized = True
    connector.use_metaapi = False

    mock_mt5.copy_rates_from_pos.reset_mock()
    mock_mt5.copy_rates_from_pos.side_effect = [None, [{'time': 123456, 'open': 1.0, 'high': 1.1, 'low': 0.9, 'close': 1.05}]]

    df = connector.get_rates("XAUUSD", "M5", 100, max_retries=2)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert mock_mt5.copy_rates_from_pos.call_count == 2

def test_get_rates_retry_failure(connector):
    """Test that get_rates raises MarketDataError after retries."""
    connector._is_initialized = True
    connector.use_metaapi = False

    mock_mt5.copy_rates_from_pos.reset_mock()
    mock_mt5.copy_rates_from_pos.side_effect = None
    mock_mt5.copy_rates_from_pos.return_value = None

    with pytest.raises(MarketDataError):
        connector.get_rates("XAUUSD", "M5", 100, max_retries=2)

    assert mock_mt5.copy_rates_from_pos.call_count == 2

def test_get_tick_retry_success(connector):
    """Test that get_tick retries and succeeds."""
    connector._is_initialized = True
    connector.use_metaapi = False

    mock_mt5.symbol_info_tick.reset_mock()
    mock_mt5.symbol_info_tick.side_effect = [None, MagicMock(bid=2000.0, ask=2001.0)]

    tick = connector.get_tick("XAUUSD", max_retries=2)

    assert tick['bid'] == 2000.0
    assert tick['ask'] == 2001.0
    assert mock_mt5.symbol_info_tick.call_count == 2

def test_place_order_execution_error(connector):
    """Test that place_order raises OrderExecutionError on MT5 rejection."""
    connector._is_initialized = True
    connector.use_metaapi = False

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )

    with patch.object(connector, 'get_tick', return_value={'bid': 2000.0, 'ask': 2001.0}):
        mock_mt5.order_send.reset_mock()
        mock_result = MagicMock()
        mock_result.retcode = 10001 # Some error code
        mock_result.comment = "Invalid volume"
        mock_mt5.order_send.return_value = mock_result

        with pytest.raises(OrderExecutionError) as excinfo:
            connector.place_order(signal)

        assert "Order rejected: Invalid volume" in str(excinfo.value)
