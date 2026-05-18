import unittest
from unittest.mock import MagicMock

from src.core.config import TradingConfig
from src.core.constants import SignalDirection
from src.models.base_model import Signal
from src.models.ensemble import EnsembleModel
from src.models.regime_detector import MarketRegime, RegimeInfo


class TestRegimeAlignmentSafety(unittest.TestCase):
    def setUp(self):
        self.config = MagicMock(spec=TradingConfig)
        self.config.model_drift_threshold = 0.3
        self.ensemble = EnsembleModel(config=self.config)
        # Mock sub-agents to avoid loading weights
        self.ensemble.ppo_agent = MagicMock()
        self.ensemble.dreamer_agent = MagicMock()
        self.ensemble.lstm_model = MagicMock()

        # Default high-confidence signals
        self.signals = {
            "ppo": Signal(direction=SignalDirection.BUY, confidence=0.9),
            "dreamer": Signal(direction=SignalDirection.BUY, confidence=0.9),
            "lstm": Signal(direction=SignalDirection.BUY, confidence=0.9),
        }

        # Mock DynamicEnsemble metrics to avoid drift penalty
        self.ensemble.dynamic_ensemble.calculate_metrics = MagicMock(
            return_value={"accuracy": 0.8, "drift_score": 0.0, "calibration_error": 0.0}
        )
        self.ensemble.dynamic_ensemble.get_weights = MagicMock(
            return_value={"ppo": 0.333, "dreamer": 0.333, "lstm": 0.334}
        )

    def test_high_stability_alignment(self):
        """Scenario A: High stability and alignment should result in no penalty."""
        regime_info = RegimeInfo(
            label=MarketRegime.TRENDING,
            confidence=0.9,
            transition_score=0.1,
            volatility_index=1.0,
            session_alignment=1.0,
            volatility_alignment=1.0,
            transition_probabilities={"trending": 0.9},
            raw_features={},
        )

        result = self.ensemble.aggregate_signals(self.signals, regime_info=regime_info)

        self.assertEqual(result.direction, SignalDirection.BUY)
        self.assertAlmostEqual(result.confidence, 0.9)
        self.assertNotIn("market_context_penalty", result.metadata)

    def test_moderate_misalignment_penalty(self):
        """Scenario B: Moderate instability should trigger a confidence penalty."""
        # Lower alignment and higher transition score
        # context_stability = (0.6 + 0.6 + 0.6 + (1.0 - 0.4)) / 4 = 0.6
        regime_info = RegimeInfo(
            label=MarketRegime.RANGING,
            confidence=0.6,
            transition_score=0.4,
            volatility_index=1.2,
            session_alignment=0.6,
            volatility_alignment=0.6,
            transition_probabilities={"ranging": 0.6, "trending": 0.4},
            raw_features={},
        )

        result = self.ensemble.aggregate_signals(self.signals, regime_info=regime_info)

        self.assertEqual(result.direction, SignalDirection.BUY)
        self.assertLess(result.confidence, 0.9)
        self.assertIn("market_context_penalty", result.metadata)
        # Stability 0.6 is < 0.7 trigger
        # Penalty = (0.7 - 0.6) * 0.5 = 0.05 (5% reduction)
        # Expected confidence = 0.9 * 0.95 = 0.855
        self.assertAlmostEqual(result.confidence, 0.855, places=3)

    def test_critical_misalignment_hold(self):
        """Scenario C: Critical instability should force a HOLD."""
        # Very low alignment and high transition probability
        # context_stability = (0.3 + 0.2 + 0.2 + (1.0 - 0.7)) / 4 = 0.25
        regime_info = RegimeInfo(
            label=MarketRegime.NEWS_SHOCK,
            confidence=0.3,
            transition_score=0.7,
            volatility_index=3.5,
            session_alignment=0.2,
            volatility_alignment=0.2,
            transition_probabilities={"news_shock": 0.3, "volatile_breakout": 0.7},
            raw_features={},
        )

        result = self.ensemble.aggregate_signals(self.signals, regime_info=regime_info)

        self.assertEqual(result.direction, SignalDirection.HOLD)
        self.assertEqual(result.metadata.get("reason"), "Critical market context instability")
        self.assertAlmostEqual(result.metadata.get("market_context_stability"), 0.25)


if __name__ == "__main__":
    unittest.main()
