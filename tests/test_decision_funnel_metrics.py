"""
Tests for Decision Funnel Metrics.
Ensures that signal rejections across RiskManager, ExecutionFilter, and CapitalAllocator
are correctly recorded in Prometheus metrics.
"""
import unittest
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from src.core.monitor import INTERNAL_REJECTION_COUNTER, Monitor
from src.core.schemas import TradeSignal
from src.trading.audited_risk_manager import AuditedRiskManager
from src.trading.capital_allocator import CapitalAllocator, RejectionCode
from src.trading.execution_filter import ExecutionFilter


class TestDecisionFunnelMetrics(unittest.TestCase):
    def setUp(self):
        self.config = MagicMock()
        # Mocking SecretStr for telegram_token
        self.config.telegram_token.get_secret_value.return_value = ""
        self.config.telegram_chat_id = "fake_chat_id"
        self.config.max_positions = 5
        self.config.max_losing_streak = 5
        self.config.max_daily_loss = 0.05
        self.config.model_drift_threshold = 0.3
        self.config.model_accuracy_floor = 0.45
        self.config.model_calibration_threshold = 0.25
        self.config.signal_flicker_window = 6
        self.config.max_signal_changes = 3

        with patch('telegram.Bot'):
            self.monitor = Monitor(self.config)

    def test_audited_risk_manager_rejection_metrics_symbol(self):
        # Setup AuditedRiskManager with monitor
        risk = AuditedRiskManager(self.config, account_balance=10000.0, monitor=self.monitor)

        # Create a signal that will be rejected (e.g., symbol not in portfolio)
        # Using model_construct to bypass Pydantic validation (including SYMBOL_PATTERN)
        signal = TradeSignal.model_construct(
            symbol="INVALID_SYM",
            direction=1,
            entry_price=2000.0,
            stop_loss=1950.0,
            take_profit=2100.0,
            lot_size=0.1,
            algorithm="test",
            confidence=0.8
        )

        with patch.object(INTERNAL_REJECTION_COUNTER, "labels") as mock_labels:
            mock_counter = MagicMock()
            mock_labels.return_value = mock_counter

            risk.approve(signal)

            mock_labels.assert_any_call(component="risk_manager", reason="SYMBOL_ALLOCATION")
            mock_counter.inc.assert_called()

    def test_audited_risk_manager_rejection_metrics_confidence(self):
        # Setup AuditedRiskManager with monitor
        risk = AuditedRiskManager(self.config, account_balance=10000.0, monitor=self.monitor)

        # Trigger rejection by setting confidence too low
        signal = TradeSignal.model_construct(
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            stop_loss=1950.0,
            take_profit=2100.0,
            lot_size=0.1,
            algorithm="test",
            confidence=0.1
        )

        with patch.object(INTERNAL_REJECTION_COUNTER, "labels") as mock_labels:
            mock_counter = MagicMock()
            mock_labels.return_value = mock_counter

            risk.approve(signal)

            # Should be called for "MIN_CONFIDENCE"
            self.assertTrue(mock_labels.called)
            mock_labels.assert_any_call(component="risk_manager", reason="MIN_CONFIDENCE")
            mock_counter.inc.assert_called()

    def test_execution_filter_rejection_metrics(self):
        # Setup ExecutionFilter with monitor
        self.config.max_drawdown = 0.15
        ef = ExecutionFilter(config=self.config, monitor=self.monitor)

        signal = TradeSignal.model_construct(
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            stop_loss=1950.0,
            take_profit=2100.0,
            lot_size=0.1,
            algorithm="test",
            confidence=0.4 # Low confidence to trigger block
        )

        # Configure thresholds to trigger block
        self.config.min_confidence = 0.7
        self.config.volatility_extreme_threshold = 3.0

        with patch.object(INTERNAL_REJECTION_COUNTER, "labels") as mock_labels:
            mock_counter = MagicMock()
            mock_labels.return_value = mock_counter

            # Use a fixed weekday timestamp to avoid SESSION_CLOSED rejections on weekends
            weekday_ts = datetime(2026, 5, 13, 12, 0, 0, tzinfo=UTC) # Wednesday

            # Mock market data as empty to avoid calculation errors
            ef.validate(signal, market_data=None, timestamp=weekday_ts)

            mock_labels.assert_any_call(component="execution_filter", reason="CONFIDENCE_THRESHOLD")
            mock_counter.inc.assert_called()

    def test_capital_allocator_rejection_metrics(self):
        # Setup CapitalAllocator with monitor
        allocator = CapitalAllocator(total_budget=0.0, monitor=self.monitor)

        with patch.object(INTERNAL_REJECTION_COUNTER, "labels") as mock_labels:
            mock_counter = MagicMock()
            mock_labels.return_value = mock_counter

            allocator.request_allocation("STRAT_1", 0.02)

            mock_labels.assert_any_call(component="capital_allocator", reason=RejectionCode.NO_BUDGET.value)
            mock_counter.inc.assert_called()

if __name__ == "__main__":
    unittest.main()
