"""Unit tests for Backtester and related components."""

import unittest
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from src.trading.backtester import Backtester, PerformanceReport, TradeRecord

class MockModel:
    def predict(self, obs):
        # Always return BUY with 0.8 confidence
        return 1, 0.8, {"mock": 1}

class TestBacktester(unittest.TestCase):
    def setUp(self):
        self.backtester = Backtester(initial_balance=10000.0)

        # Create mock OHLCV data
        dates = pd.date_range(start="2023-01-01", periods=3000, freq="5min")
        data = {
            "open": np.linspace(1900, 2000, 3000),
            "high": np.linspace(1905, 2005, 3000),
            "low": np.linspace(1895, 1995, 3000),
            "close": np.linspace(1900, 2000, 3000),
            "tick_volume": np.random.randint(100, 1000, 3000)
        }
        self.df = pd.DataFrame(data, index=dates)

    def test_calculate_metrics(self):
        trades = [
            TradeRecord(
                entry_time=datetime(2023, 1, 1),
                exit_time=datetime(2023, 1, 2),
                direction=1,
                entry_price=1900.0,
                exit_price=1910.0,
                pnl=100.0,
                mae=5.0,
                mfe=15.0
            ),
            TradeRecord(
                entry_time=datetime(2023, 1, 2),
                exit_time=datetime(2023, 1, 3),
                direction=-1,
                entry_price=1910.0,
                exit_price=1900.0,
                pnl=100.0,
                mae=5.0,
                mfe=15.0
            )
        ]
        report = self.backtester._calculate_metrics(trades)
        self.assertEqual(report.total_trades, 2)
        self.assertEqual(report.win_rate, 1.0)
        self.assertGreater(report.annualized_return, 0)
        self.assertEqual(report.profit_factor, 0.0)  # Gross loss is 0, so pf is 0.0 in current impl

    def test_run_backtest(self):
        # This will test the full pipeline including FeatureEngineer and ExecutionFilter
        # Since TA-Lib might not be installed, we check if it runs or logs warning
        model = MockModel()
        try:
            report, trades = self.backtester.run(self.df, model, train_window=1000, test_window=500)
            self.assertIsInstance(report, PerformanceReport)
            self.assertIsInstance(trades, list)
        except Exception as e:
            # If it fails because of TA-Lib missing, that's expected in some environments
            if "TA-Lib" in str(e):
                self.skipTest("TA-Lib not installed")
            else:
                raise e

if __name__ == "__main__":
    unittest.main()
