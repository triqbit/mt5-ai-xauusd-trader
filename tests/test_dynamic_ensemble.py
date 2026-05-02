import unittest

from src.models.dynamic_ensemble import DynamicEnsemble
from src.models.regime_detector import MarketRegime, RegimeInfo


class TestDynamicEnsemble(unittest.TestCase):
    def setUp(self):
        self.models = ["ppo", "lstm", "transformer"]
        self.ensemble = DynamicEnsemble(
            model_names=self.models,
            smoothing_factor=0.5,  # Faster for testing
            max_swing=0.1,
        )

    def test_initial_weights(self):
        weights = self.ensemble.get_weights()
        for name in self.models:
            self.assertAlmostEqual(weights[name], 1.0 / 3.0)

    def test_weight_adaptation(self):
        # "ppo" is doing great, "lstm" is bad
        metrics = {
            "ppo": {"accuracy": 0.9, "calibration_error": 0.0, "drift_score": 0.0},
            "lstm": {"accuracy": 0.1, "calibration_error": 0.5, "drift_score": 0.5},
            "transformer": {"accuracy": 0.5, "calibration_error": 0.1, "drift_score": 0.1},
        }
        initial_weights = self.ensemble.get_weights().copy()

        # Multiple updates to see movement
        for _ in range(5):
            new_weights = self.ensemble.update_weights(metrics)

        self.assertGreater(new_weights["ppo"], initial_weights["ppo"])
        self.assertLess(new_weights["lstm"], initial_weights["lstm"])

    def test_volatility_impact(self):
        # High calibration error on PPO
        metrics = {
            "ppo": {"accuracy": 0.8, "calibration_error": 0.8, "drift_score": 0.0},
            "lstm": {"accuracy": 0.5, "calibration_error": 0.0, "drift_score": 0.0},
            "transformer": {"accuracy": 0.5, "calibration_error": 0.0, "drift_score": 0.0},
        }
        # Use UNKNOWN regime to isolate volatility impact
        # Low volatility: calibration error has NO extra penalty
        regime_low = RegimeInfo(
            label=MarketRegime.UNKNOWN, confidence=1.0, transition_score=0.0, volatility_index=0.5
        )

        # Run multiple updates to reach steady state
        for _ in range(10):
            self.ensemble.update_weights(metrics, regime_info=regime_low)
        w_low = self.ensemble.get_weights()["ppo"]

        # Reset weights
        self.ensemble.weights = dict.fromkeys(self.models, 1.0 / 3.0)
        self.ensemble._target_weights = self.ensemble.weights.copy()
        self.ensemble._prev_target_weights = self.ensemble.weights.copy()

        # High volatility: calibration error has severe penalty (score -= 0.3 * cal)
        regime_high = RegimeInfo(
            label=MarketRegime.UNKNOWN, confidence=1.0, transition_score=0.0, volatility_index=5.0
        )
        for _ in range(10):
            self.ensemble.update_weights(metrics, regime_info=regime_high)
        w_high = self.ensemble.get_weights()["ppo"]

        self.assertLess(w_high, w_low)

    def test_swing_cap(self):
        # Extreme change in metrics
        metrics = {
            "ppo": {"accuracy": 1.0},
            "lstm": {"accuracy": 0.0},
            "transformer": {"accuracy": 0.0},
        }
        current_ppo_weight = self.ensemble.weights["ppo"]
        new_weights = self.ensemble.update_weights(metrics)

        # Max swing is 0.1, so it shouldn't jump to 1.0 immediately
        self.assertLessEqual(new_weights["ppo"], current_ppo_weight + 0.11)

    def test_oscillation_dampening(self):
        # Force target to flip-flop
        metrics_a = {
            "ppo": {"accuracy": 1.0},
            "lstm": {"accuracy": 0.0},
            "transformer": {"accuracy": 0.0},
        }
        metrics_b = {
            "ppo": {"accuracy": 0.0},
            "lstm": {"accuracy": 1.0},
            "transformer": {"accuracy": 0.0},
        }

        self.ensemble.update_weights(metrics_a)  # Target ppo high
        w1 = self.ensemble.weights["ppo"]

        self.ensemble.update_weights(metrics_b)  # Target ppo low
        w2 = self.ensemble.weights["ppo"]

        self.ensemble.update_weights(metrics_a)  # Target ppo high again (reversal)
        w3 = self.ensemble.weights["ppo"]

        # Step size from w2 to w3 (reversal) should be smaller than step from initial to w1
        # because alpha is dampened during oscillation.
        step1 = abs(w1 - (1.0 / 3.0))
        step3 = abs(w3 - w2)

        self.assertLess(step3, step1)

    def test_min_weight(self):
        metrics = {
            "ppo": {"accuracy": 1.0},
            "lstm": {"accuracy": 0.0},
            "transformer": {"accuracy": 0.0},
        }
        for _ in range(20):
            weights = self.ensemble.update_weights(metrics)

        for name in self.models:
            self.assertGreaterEqual(weights[name], self.ensemble.min_weight - 1e-6)


if __name__ == "__main__":
    unittest.main()
