from src.trading.mt5_connector import MT5Connector


def test_mt5_failover_to_metaapi(test_config, mock_mt5, mock_metaapi, monkeypatch):
    # Setup MT5 to fail initialization
    mock_mt5.initialize.return_value = False

    connector = MT5Connector(test_config)

    # Execution
    success = connector.initialize()

    # Validation
    assert success is True
    assert connector.use_metaapi is True
    mock_mt5.initialize.assert_called_once()
    mock_metaapi.assert_called_once_with(test_config.metaapi_token)

def test_graceful_degradation_all_failed(test_config, mock_mt5, mock_metaapi, monkeypatch):
    # Setup both to fail
    mock_mt5.initialize.return_value = False
    # MetaAPI mock already exists, but we can make it fail by removing the token or mocking the class to raise
    monkeypatch.setattr(test_config, "metaapi_token", "")

    connector = MT5Connector(test_config)

    # Execution
    success = connector.initialize()

    # Validation
    assert success is False
    assert connector._is_initialized is False

def test_graceful_degradation_in_trading_loop(test_config, connector, mock_mt5):
    # Mocking a failed tick fetch
    connector._is_initialized = True
    connector.use_metaapi = False
    mock_mt5.symbol_info_tick.return_value = None

    tick = connector.get_tick("XAUUSD")

    assert tick == {"bid": 0.0, "ask": 0.0}
