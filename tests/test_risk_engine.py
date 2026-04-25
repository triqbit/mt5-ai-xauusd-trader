import unittest
from unittest.mock import MagicMock
from src.trading.risk_engine import RiskEngine, TradeSignal
from src.core.config import TradingConfig

class TestRiskEngine(unittest.TestCase):
    def setUp(self):
        self.config = MagicMock(spec=TradingConfig)
        self.config.risk_per_trade = 0.01
        self.config.daily_loss_limit_lv4 = 0.05
        self.config.daily_loss_limit_lv3 = 0.04
        self.config.daily_loss_limit_lv2 = 0.03
        self.config.drawdown_limit_lv5 = 0.30
        self.config.drawdown_limit_lv4 = 0.25
        self.config.drawdown_limit_lv3 = 0.20
        self.config.drawdown_limit_lv2 = 0.15
        self.config.min_confidence = 0.55
        self.config.max_concurrent_positions = 5

        self.engine = RiskEngine(self.config, account_balance=10000.0)

    def test_approve_success(self):
        signal = TradeSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=2020.0,
            lot_size=0.1,
            algorithm="ppo",
            confidence=0.7
        )
        self.assertTrue(self.engine.approve(signal))

    def test_circuit_breaker_drawdown(self):
        self.engine.peak_equity = 10000.0
        self.engine.balance = 6000.0 # 40% drawdown
        self.assertFalse(self.engine.check_circuit_breaker())

    def test_size_position_scaling(self):
        # ATR-based sizing
        self.engine.daily.realised_pnl = -450.0 # 4.5% loss on 10000.0 peak equity
        self.engine.daily.peak_equity = 10000.0

        # Lv3 loss limit hit, should scale by 0.25
        size = self.engine.size_position("XAUUSD", atr=10.0)
        # risk_amount = 10000 * 0.01 * 0.25 = 25
        # lot_size = 25 / (10 * 200) = 0.0125 -> 0.01
        self.assertEqual(size, 0.01)

if __name__ == "__main__":
    unittest.main()
