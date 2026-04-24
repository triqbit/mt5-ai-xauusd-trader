import unittest
from unittest.mock import MagicMock
from src.trading.risk_engine import RiskEngine
from src.core.config import TradingConfig

class TestRiskEngine(unittest.TestCase):
    def setUp(self):
        self.config = TradingConfig(
            mt5_password="test",
            mt5_server="test",
            daily_loss_limit_l2=0.03,
            daily_loss_limit_l3=0.04,
            daily_loss_limit_l4=0.05,
            drawdown_limit_l2=0.15,
            drawdown_limit_l3=0.20,
            drawdown_limit_l4=0.25,
            drawdown_limit_l5=0.30
        )
        self.engine = RiskEngine(self.config, initial_equity=10000.0)

    def test_daily_loss_multipliers(self):
        # 3.5% loss -> L2 hit (0.5x)
        self.engine.record_trade_close(-350.0)
        self.assertEqual(self.engine.get_position_size_multiplier(), 0.5)

        # 4.5% loss -> L3 hit (0.25x)
        self.engine.record_trade_close(-100.0) # Total 450
        self.assertEqual(self.engine.get_position_size_multiplier(), 0.25)

        # 5.5% loss -> L4 hit (HALT)
        self.engine.record_trade_close(-100.0) # Total 550
        self.assertEqual(self.engine.get_position_size_multiplier(), 0.0)
        self.assertTrue(self.engine.trading_halted)

    def test_drawdown_circuit_breaker(self):
        # 16% drawdown
        self.engine.update_equity(8400.0)
        self.assertEqual(self.engine.get_position_size_multiplier(), 0.75)

        # 31% drawdown -> EMERGENCY STOP
        self.engine.update_equity(6900.0)
        self.assertEqual(self.engine.get_position_size_multiplier(), 0.0)
        self.assertTrue(self.engine.emergency_stop)

    def test_calculate_atr_position_size(self):
        # Normal volatility
        size = self.engine.calculate_atr_position_size(
            atr_14=1.0,
            atr_30_avg=1.0,
            risk_amount_dollars=100.0,
            tick_value=1.0,
            tick_size=0.01
        )
        # Risk 100 / (1.0 * 100) = 1.0 lot
        self.assertEqual(size, 1.0)

        # High volatility (2.5x) -> 0.5x multiplier
        size_high_vol = self.engine.calculate_atr_position_size(
            atr_14=2.5,
            atr_30_avg=1.0,
            risk_amount_dollars=100.0,
            tick_value=1.0,
            tick_size=0.01
        )
        # Risk 100 / (2.5 * 100) = 0.4 lot. Then 0.5x for vol = 0.2 lot.
        self.assertEqual(size_high_vol, 0.2)

if __name__ == "__main__":
    unittest.main()
