import sys
import unittest
from unittest.mock import MagicMock, patch
import structlog
import uuid
from main import run_live, configure_logging
from src.trading.risk_manager import TradeSignal
from src.core.constants import SignalDirection

class TestObservability(unittest.TestCase):
    def setUp(self):
        # Configure logging to capture output
        self.log_output = []
        def test_processor(logger, name, event_dict):
            self.log_output.append(event_dict.copy())
            return event_dict

        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                test_processor,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.BoundLogger,
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
        )

    @patch("main.MT5Connector")
    @patch("main.RiskManager")
    @patch("main.EnsembleModel")
    @patch("main.TradeLogger")
    @patch("main.Monitor")
    @patch("main.time.sleep", side_effect=InterruptedError) # To break the loop
    def test_decision_record_and_trace_id(self, mock_monitor, mock_logger, mock_model, mock_risk, mock_connector, mock_sleep):
        # Setup mocks
        cfg = MagicMock()
        cfg.symbol = "XAUUSD"
        cfg.mode = "demo"
        cfg.algorithm = "ensemble"
        cfg.timeframe = "M5"

        connector = mock_connector.return_value
        connector.get_ohlcv.return_value = MagicMock()
        connector.get_tick.return_value = {"ask": 2000.0, "bid": 1999.0}
        connector.get_account_balance.return_value = 10000.0
        connector.get_positions.return_value = []

        risk = mock_risk.return_value
        risk.approve.return_value = {
            "passed": True,
            "rejection_reasons": [],
            "risk_reward": 2.0,
            "drawdown_impact": 0.0,
            "kelly_fraction": 0.1,
            "summary": "All good"
        }
        risk.open_positions = {}

        model = mock_model.return_value
        model.predict.return_value = (SignalDirection.BUY, 0.8, {"ppo": 0}) # 0 is BUY in legacy map used by SignalExplainer
        model.weights = {"ppo": 1.0}

        # Run one iteration (it will hit InterruptedError via sleep)
        try:
            run_live(cfg, connector, risk, model, mock_logger.return_value, mock_monitor.return_value)
        except InterruptedError:
            pass

        # Verify logs
        decision_record = next((log for log in self.log_output if log.get("event") == "decision_record"), None)
        self.assertIsNotNone(decision_record)
        self.assertIn("trace_id", decision_record)
        self.assertEqual(decision_record["symbol"], "XAUUSD")
        self.assertEqual(decision_record["direction"], SignalDirection.BUY)
        self.assertEqual(decision_record["approved"], True)

        # Verify performance metrics also have trace_id
        perf_metric = next((log for log in self.log_output if log.get("event") == "performance_metric"), None)
        if perf_metric:
            self.assertIn("trace_id", perf_metric)
            self.assertEqual(perf_metric["trace_id"], decision_record["trace_id"])

if __name__ == "__main__":
    unittest.main()
