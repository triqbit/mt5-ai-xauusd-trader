"""
Tests for src/core/decision_support.py
"""

import unittest
from unittest.mock import MagicMock
from datetime import datetime, timezone
from src.core.decision_support import (
    DecisionSupport, SignalSummary, DecisionPacket,
    ModelConsensus, MarketRegime, RiskState,
    BlockedConditions, PerformanceContext, ExplainabilityPayload
)

class TestDecisionSupport(unittest.TestCase):

    def setUp(self):
        self.ds = DecisionSupport()
        self.mock_risk_manager = MagicMock()
        self.mock_risk_manager.peak_equity = 10000.0
        self.mock_risk_manager.balance = 9500.0
        self.mock_risk_manager.daily.realised_pnl = -200.0
        self.mock_risk_manager.daily.peak_equity = 10000.0
        self.mock_risk_manager.open_positions = {}
        self.mock_risk_manager.cfg.max_positions = 3
        self.mock_risk_manager.validate_signal_full.return_value = (True, [])

        self.mock_ensemble = MagicMock()
        self.mock_ensemble.weights = {"ppo": 0.4, "lstm": 0.6}

        self.perf_metrics = {
            "sharpe_ratio": 1.5,
            "profit_factor": 2.1,
            "win_rate": 0.65,
            "total_trades": 100
        }

    def test_signal_summary_validation(self):
        sig = SignalSummary(
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            lot_size=0.1,
            confidence=0.8,
            algorithm="ensemble"
        )
        self.assertEqual(sig.symbol, "XAUUSD")
        self.assertEqual(sig.direction, 1)

    def test_generate_packet(self):
        sig = SignalSummary(
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=2020.0,
            lot_size=0.1,
            confidence=0.8,
            algorithm="ensemble"
        )

        packet = self.ds.generate_packet(
            sig, self.mock_risk_manager, self.mock_ensemble, self.perf_metrics
        )

        self.assertIsInstance(packet, DecisionPacket)
        self.assertEqual(packet.signal.symbol, "XAUUSD")
        self.assertFalse(packet.blocked.is_blocked)
        self.assertEqual(packet.performance.total_trades, 100)
        self.assertEqual(packet.risk.current_drawdown, 0.05)

    def test_format_for_operator(self):
        # Smoke test for rich formatting
        sig = SignalSummary(
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=2020.0,
            lot_size=0.1,
            confidence=0.8,
            algorithm="ensemble"
        )
        packet = self.ds.generate_packet(
            sig, self.mock_risk_manager, self.mock_ensemble, self.perf_metrics
        )

        # Should not raise exception
        self.ds.format_for_operator(packet)

    def test_blocked_signal_packet(self):
        self.mock_risk_manager.validate_signal_full.return_value = (False, ["Daily loss limit reached"])
        sig = SignalSummary(
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            lot_size=0.1,
            confidence=0.8,
            algorithm="ensemble"
        )

        packet = self.ds.generate_packet(
            sig, self.mock_risk_manager, self.mock_ensemble, self.perf_metrics
        )

        self.assertTrue(packet.blocked.is_blocked)
        self.assertIn("Daily loss limit reached", packet.blocked.reasons)

if __name__ == "__main__":
    unittest.main()
