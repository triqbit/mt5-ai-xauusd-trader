"""
Enhanced observability tests for Jules02 improvements.
Verifies trace_id propagation and new Prometheus metrics.
"""
import unittest
from unittest.mock import MagicMock, patch
import uuid
import structlog
import structlog.contextvars
from datetime import datetime, UTC

from src.core.schemas import TradeSignal
from src.core.monitor import (
    Monitor,
    MARKET_REGIME_GAUGE,
    REGIME_CONFIDENCE_GAUGE,
    PORTFOLIO_HEAT_TOTAL_GAUGE,
    PORTFOLIO_HEAT_SYMBOL_GAUGE,
    DRAWDOWN_GAUGE
)
from src.trading.mt5_connector import MT5Connector
from src.trading.capital_allocator import CapitalAllocator, StrategyConfig
from src.trading.risk_manager import RiskManager

class TestEnhancedObservability(unittest.TestCase):
    def setUp(self):
        self.config = MagicMock()
        self.config.telegram_token.get_secret_value.return_value = ""
        self.config.telegram_chat_id = "fake"
        self.config.prometheus_port = 8000
        self.config.algorithm = "ensemble"
        self.config.symbol = "XAUUSD"
        self.config.mt5_path = ""
        self.config.mt5_login = 12345
        self.config.mt5_password.get_secret_value.return_value = "pass"
        self.config.mt5_server = "server"

        # Monitor
        with patch('telegram.Bot'):
            self.monitor = Monitor(self.config)

    def test_trace_id_propagation_to_signal(self):
        """Verifies that trace_id can be set in TradeSignal."""
        trace_id = str(uuid.uuid4())
        signal = TradeSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            stop_loss=1980.0,
            take_profit=2040.0,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=0.8,
            trace_id=trace_id
        )
        self.assertEqual(signal.trace_id, trace_id)

    def test_mt5_connector_trace_id_correlation(self):
        """Verifies that trace_id is included in MT5 order comment."""
        trace_id = "abcd-1234-efgh-5678"
        signal = TradeSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            stop_loss=1980.0,
            take_profit=2040.0,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=0.8,
            trace_id=trace_id
        )

        connector = MT5Connector(self.config)
        connector._is_initialized = True
        connector.use_metaapi = False

        with patch('src.trading.mt5_connector.mt5') as mock_mt5:
            mock_tick = MagicMock()

            mock_tick.ask = 2000.0
            mock_tick.bid = 1999.0
            mock_mt5.symbol_info_tick.return_value = mock_tick

            mock_result = MagicMock()
            mock_result.retcode = 10009 # TRADE_RETCODE_DONE
            mock_result.order = 123456
            mock_result.comment = "DONE"
            mock_mt5.TRADE_RETCODE_DONE = 10009
            mock_mt5.order_send.return_value = mock_result

            connector.place_order(signal)

            mock_mt5.order_send.assert_called()
            args, kwargs = mock_mt5.order_send.call_args
            request = args[0]
            self.assertIn("AI:ensemble:abcd-123", request["comment"])

    def test_market_regime_metrics(self):
        """Verifies market regime metrics are updated."""
        with patch.object(MARKET_REGIME_GAUGE, 'set') as mock_set, \
             patch.object(REGIME_CONFIDENCE_GAUGE, 'set') as mock_conf_set:

            self.monitor.update_market_regime("trending", 0.85)

            mock_set.assert_called_with(1) # trending mapping
            mock_conf_set.assert_called_with(0.85)

    def test_portfolio_heat_metrics(self):
        """Verifies portfolio heat metrics are updated in CapitalAllocator."""
        allocator = CapitalAllocator(total_budget=10000.0, monitor=self.monitor)
        allocator.add_strategy(StrategyConfig(
            strategy_id="strat1",
            symbol="XAUUSD",
            model_family="ensemble",
            capital_cap=5000.0
        ))

        with patch.object(PORTFOLIO_HEAT_TOTAL_GAUGE, 'set') as mock_total_set, \
             patch.object(PORTFOLIO_HEAT_SYMBOL_GAUGE, 'labels') as mock_labels:

            mock_sym_gauge = MagicMock()
            mock_labels.return_value = mock_sym_gauge

            # Risk 2% of 10000 = 200.
            # Heat = 200 / 10000 = 0.02
            allocator.request_allocation("strat1", 0.02)

            mock_total_set.assert_called()
            self.assertAlmostEqual(mock_total_set.call_args[0][0], 0.02)
            mock_labels.assert_called_with(symbol="XAUUSD")
            mock_sym_gauge.set.assert_called()
            self.assertAlmostEqual(mock_sym_gauge.set.call_args[0][0], 0.02)

    def test_continuous_drawdown_metric(self):
        """Verifies DRAWDOWN_GAUGE is updated in RiskManager."""
        risk = RiskManager(self.config, account_balance=10000.0, monitor=self.monitor)

        with patch.object(DRAWDOWN_GAUGE, 'set') as mock_set:
            # Drop balance to 9000 -> 10% drawdown
            risk.update_equity(9000.0)

            mock_set.assert_called_with(10.0)

if __name__ == "__main__":
    unittest.main()
