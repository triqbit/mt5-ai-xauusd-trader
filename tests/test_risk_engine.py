import unittest
from unittest.mock import MagicMock
from src.trading.risk_engine import RiskEngine
from src.core.config import TradingConfig

class TestRiskEngine(unittest.TestCase):
    def setUp(self):
        self.config = TradingConfig(
            mt5_password="test",
            mt5_server="test",
            drawdown_level_2=0.15,
            drawdown_level_3=0.20,
            drawdown_level_4=0.25,
            drawdown_level_5=0.30,
            daily_loss_level_2=0.03,
            daily_loss_level_3=0.04,
            daily_loss_level_4=0.05,
            risk_per_trade=0.01,
            min_position_size=0.01,
            max_position_size_pct=0.10
        )
        # Use 100k balance for easier calculations
        self.engine = RiskEngine(self.config, 100000.0)

    def test_update_equity_peaks(self):
        self.engine.update_equity(110000.0)
        self.assertEqual(self.engine.peak_equity, 110000.0)
        self.assertEqual(self.engine.daily.peak_equity, 110000.0)

    def test_check_circuit_breaker(self):
        # Peak 100000, current 60000 -> 40% drawdown
        self.engine.update_equity(60000.0)
        self.assertFalse(self.engine.check_circuit_breaker())

    def test_get_position_size_multiplier_drawdown(self):
        # 16% drawdown -> level 2 hit -> 0.75 multiplier
        self.engine.update_equity(84000.0)
        self.assertEqual(self.engine.get_position_size_multiplier(), 0.75)

    def test_calculate_atr_lot_size(self):
        # balance 100,000, risk 1% = 1000
        # sl_distance 10, contract 100 -> lots = 1000 / (10 * 100) = 1.0

        # Adjust config for test
        self.config.max_position_size_pct = 1.0 # Allow up to 100% equity notional
        lots = self.engine.calculate_atr_lot_size("XAUUSD", 1.0, 2000.0, 1990.0)
        # Notional for 1.0 lot at 2000 is 200,000.
        # Max notional is 100,000 (100% of 100k).
        # So it should be 0.5.
        self.assertEqual(lots, 0.5)

if __name__ == "__main__":
    unittest.main()
