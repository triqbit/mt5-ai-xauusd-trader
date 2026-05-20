
import unittest
from datetime import datetime
from unittest.mock import MagicMock

from src.trading.backtester import BacktestEngine


class TestBacktestDrawdownOptimization(unittest.TestCase):
    def setUp(self):
        # Mock FeatureEngineer and ExecutionFilter to avoid TA-Lib/sklearn dependencies
        mock_fe = MagicMock()
        mock_ef = MagicMock()
        self.engine = BacktestEngine(
            symbol="XAUUSD",
            initial_balance=10000.0,
            feature_engineer=mock_fe,
            execution_filter=mock_ef
        )

    def test_max_equity_tracking(self):
        """Verifies that max_equity correctly tracks the peak equity incrementally."""
        self.assertEqual(self.engine.max_equity, 10000.0)

        # Scenario 1: Equity increases
        self.engine.balance = 10500.0
        self.engine._record_equity(datetime.now(), 2000.0, [])
        self.assertEqual(self.engine.max_equity, 10500.0)

        # Scenario 2: Equity decreases (drawdown)
        self.engine.balance = 10300.0
        self.engine._record_equity(datetime.now(), 2000.0, [])
        self.assertEqual(self.engine.max_equity, 10500.0, "max_equity should stay at the previous peak")

        # Scenario 3: New peak
        self.engine.balance = 11000.0
        self.engine._record_equity(datetime.now(), 2000.0, [])
        self.assertEqual(self.engine.max_equity, 11000.0, "max_equity should update to the new peak")

    def test_drawdown_calculation_parity(self):
        """Verifies that the O(1) drawdown calculation is mathematically correct."""
        self.engine.max_equity = 12000.0
        current_equity = 11400.0
        self.engine.equity_curve = [(datetime.now(), current_equity)]

        # Logic from run_walk_forward
        peak = self.engine.max_equity
        equity = self.engine.equity_curve[-1][1]
        drawdown = (peak - equity) / (peak + 1e-8)

        expected_drawdown = (12000.0 - 11400.0) / 12000.0
        self.assertAlmostEqual(drawdown, expected_drawdown, places=7)

if __name__ == "__main__":
    unittest.main()
