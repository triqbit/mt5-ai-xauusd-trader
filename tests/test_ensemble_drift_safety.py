import unittest
from unittest.mock import MagicMock

from src.core.config import TradingConfig
from src.core.constants import SignalDirection
from src.models.base_model import Signal
from src.models.ensemble import EnsembleModel


class TestEnsembleDriftSafety(unittest.TestCase):
    def setUp(self):
        self.config = MagicMock(spec=TradingConfig)
        self.config.model_drift_threshold = 0.3

        self.ensemble = EnsembleModel(config=self.config)
        # Mock sub-agents to avoid loading weights
        self.ensemble.ppo_agent = MagicMock()
        self.ensemble.dreamer_agent = MagicMock()
        self.ensemble.lstm_model = MagicMock()

    def test_drift_penalty_application(self):
        """Verify that high drift triggers confidence penalties."""
        # Setup signals: all sub-models agree on BUY with 0.9 confidence
        signals = {
            "ppo": Signal(direction=SignalDirection.BUY, confidence=0.9),
            "dreamer": Signal(direction=SignalDirection.BUY, confidence=0.9),
            "lstm": Signal(direction=SignalDirection.BUY, confidence=0.9)
        }

        # 1. No drift scenario
        self.ensemble.dynamic_ensemble.calculate_metrics = MagicMock(return_value={
            "accuracy": 0.8, "drift_score": 0.0, "calibration_error": 0.0
        })
        clean_signal = self.ensemble.aggregate_signals(signals)
        self.assertAlmostEqual(clean_signal.confidence, 0.9)
        self.assertNotIn("drift_penalty", clean_signal.metadata)

        # 2. High drift scenario (drift = 0.3, exceeds penalty_trigger = 0.15)
        self.ensemble.dynamic_ensemble.calculate_metrics = MagicMock(return_value={
            "accuracy": 0.5, "drift_score": 0.3, "calibration_error": 0.1
        })

        # We need to ensure weights are equal so aggregate drift is 0.3
        self.ensemble.dynamic_ensemble.get_weights = MagicMock(return_value={
            "ppo": 0.333, "dreamer": 0.333, "lstm": 0.334
        })

        drifted_signal = self.ensemble.aggregate_signals(signals)

        # Drift = 0.3, threshold = 0.3, penalty_trigger = 0.15
        # drift_excess = (0.3 - 0.15) / 0.15 = 1.0
        # drift_penalty = min(0.2, 0.2 * 1.0) = 0.2
        # Expected confidence = 0.9 * (1 - 0.2) = 0.72
        self.assertLess(drifted_signal.confidence, 0.9)
        self.assertIn("drift_penalty", drifted_signal.metadata)
        self.assertAlmostEqual(drifted_signal.confidence, 0.72, places=2)

    def test_entropy_guard_application(self):
        """Verify that divergent sub-model confidence triggers entropy penalty."""
        # Sub-models agree on BUY but with highly divergent confidence
        signals = {
            "ppo": Signal(direction=SignalDirection.BUY, confidence=0.95),
            "dreamer": Signal(direction=SignalDirection.BUY, confidence=0.45), # Divergent
            "lstm": Signal(direction=SignalDirection.BUY, confidence=0.95)
        }

        self.ensemble.dynamic_ensemble.calculate_metrics = MagicMock(return_value={
            "accuracy": 0.8, "drift_score": 0.0, "calibration_error": 0.0
        })

        # Ensure equal weights for simplicity
        self.ensemble.dynamic_ensemble.get_weights = MagicMock(return_value={
            "ppo": 0.333, "dreamer": 0.333, "lstm": 0.334
        })

        # Raw weighted confidence = (0.95*0.333 + 0.45*0.333 + 0.95*0.334) = ~0.783
        # std([0.95, 0.45, 0.95]) = ~0.235 (just below 0.25 trigger)

        # Let's make it more divergent:
        # Use 0.41 to avoid Veto Power (threshold 0.40) but still trigger high entropy
        signals["dreamer"] = Signal(direction=SignalDirection.BUY, confidence=0.41)
        # std([0.95, 0.41, 0.95]) = ~0.2545 (exceeds 0.25 trigger)

        result = self.ensemble.aggregate_signals(signals)

        self.assertIn("entropy_penalty", result.metadata)
        self.assertEqual(result.metadata["entropy_penalty"], 0.10)

        # Expected confidence (weighted) = (0.95*0.333 + 0.41*0.333 + 0.95*0.334) * 0.9
        # ~ (0.316 + 0.136 + 0.317) * 0.9 = 0.77 * 0.9 = 0.693
        self.assertLess(result.confidence, 0.77)

    def test_combined_safeguards(self):
        """Verify both safeguards can apply simultaneously."""
        signals = {
            "ppo": Signal(direction=SignalDirection.BUY, confidence=0.95),
            "dreamer": Signal(direction=SignalDirection.BUY, confidence=0.41),
            "lstm": Signal(direction=SignalDirection.BUY, confidence=0.95)
        }

        # High drift
        self.ensemble.dynamic_ensemble.calculate_metrics = MagicMock(return_value={
            "accuracy": 0.5, "drift_score": 0.3, "calibration_error": 0.1
        })
        self.ensemble.dynamic_ensemble.get_weights = MagicMock(return_value={
            "ppo": 0.333, "dreamer": 0.333, "lstm": 0.334
        })

        result = self.ensemble.aggregate_signals(signals)

        self.assertIn("drift_penalty", result.metadata)
        self.assertIn("entropy_penalty", result.metadata)

        # Base confidence ~ 0.77
        # After drift penalty (20%) -> ~0.616
        # After entropy penalty (10%) -> ~0.554
        self.assertLess(result.confidence, 0.6)

if __name__ == "__main__":
    unittest.main()
