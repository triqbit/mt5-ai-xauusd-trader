"""
Integration tests for MT5Connector resilience.
"""
import unittest
from unittest.mock import MagicMock, patch
from src.trading.mt5_connector import MT5Connector, MT5ConnectionError, MT5DataError
from src.core.config import TradingConfig

class TestMT5ConnectorResilience(unittest.TestCase):
    def setUp(self):
        self.config = MagicMock(spec=TradingConfig)
        self.config.mode = "demo"
        self.config.mt5_path = ""
        self.config.mt5_login = 12345
        self.config.mt5_password = "password"
        self.config.mt5_server = "server"
        self.config.metaapi_token = "token"

        # Patch time.sleep to speed up tests
        self.sleep_patcher = patch('time.sleep', return_value=None)
        self.sleep_patcher.start()

    def tearDown(self):
        self.sleep_patcher.stop()

    @patch('src.trading.mt5_connector.mt5')
    @patch('src.trading.mt5_connector.MT5_AVAILABLE', True)
    @patch('src.trading.mt5_connector.METAAPI_AVAILABLE', False)
    def test_initialize_retry_success(self, mock_mt5):
        # Fail twice, succeed on third attempt
        mock_mt5.initialize.side_effect = [False, False, True]
        mock_mt5.last_error.return_value = "timeout"

        connector = MT5Connector(self.config)
        result = connector.initialize()

        self.assertTrue(result)
        self.assertEqual(mock_mt5.initialize.call_count, 3)

    @patch('src.trading.mt5_connector.mt5')
    @patch('src.trading.mt5_connector.MT5_AVAILABLE', True)
    @patch('src.trading.mt5_connector.METAAPI_AVAILABLE', False)
    def test_initialize_exhausted_retries(self, mock_mt5):
        mock_mt5.initialize.return_value = False
        mock_mt5.last_error.return_value = "permanent failure"

        connector = MT5Connector(self.config)
        with self.assertRaises(MT5ConnectionError):
            connector.initialize()

        # 1 original + 3 retries = 4 calls
        self.assertEqual(mock_mt5.initialize.call_count, 4)

    @patch('src.trading.mt5_connector.mt5')
    @patch('src.trading.mt5_connector.MT5_AVAILABLE', True)
    def test_get_rates_retry_on_data_error(self, mock_mt5):
        connector = MT5Connector(self.config)
        connector._is_initialized = True
        connector.use_metaapi = False

        # Fail once with None (triggering MT5DataError), then succeed
        mock_mt5.copy_rates_from_pos.side_effect = [None, [{"time": 12345, "open": 1.0}]]
        mock_mt5.last_error.return_value = "no data"

        rates = connector.get_rates("XAUUSD", "M5", 10)

        self.assertFalse(rates.empty)
        self.assertEqual(mock_mt5.copy_rates_from_pos.call_count, 2)

    @patch('src.trading.mt5_connector.MetaApi')
    @patch('src.trading.mt5_connector.MT5_AVAILABLE', False)
    @patch('src.trading.mt5_connector.METAAPI_AVAILABLE', True)
    def test_metaapi_circuit_breaker(self, mock_metaapi_cls):
        # MetaAPI fails consistently
        mock_metaapi_cls.side_effect = Exception("cloud down")

        connector = MT5Connector(self.config)

        # Failure threshold in connector is 3 for metaapi breaker
        for _ in range(3):
            with self.assertRaises(MT5ConnectionError):
                connector.initialize()

        # 4th call should be blocked by circuit breaker without calling MetaApi again
        from src.core.error_handler import CircuitBreakerError
        # initialize wraps breaker.call, but re-raises MT5ConnectionError unless we check the breaker directly
        # Actually initialize catches Exception and logs, then raises MT5ConnectionError

        with self.assertRaises(MT5ConnectionError):
             connector.initialize()

        # MetaApi should have been called only 3 times
        self.assertEqual(mock_metaapi_cls.call_count, 3)
        self.assertEqual(connector._metaapi_breaker.state.name, "OPEN")

if __name__ == '__main__':
    unittest.main()
