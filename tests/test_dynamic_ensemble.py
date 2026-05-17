import unittest
from datetime import datetime, timezone

from src.core.constants import SignalDirection
from src.models.dynamic_ensemble import DynamicEnsemble
from src.models.regime_detector import MarketRegime, RegimeInfo


class TestDynamicEnsemble(unittest.TestCase):
    """
    Comprehensive test suite for DynamicEnsemble weighting engine.
    Covers adaptation, stability, regime-awareness, and autonomous tracking.
    """

    def setUp(self):
        self.models = ["ppo", "lstm", "transformer"]
        self.ensemble = DynamicEnsemble(
            model_names=self.models,
            smoothing_factor=0.5,  # Faster for testing
            max_swing=0.1,
        )

    def test_initial_weights(self):
        """Verify that weights are initialized equally by default."""
        weights = self.ensemble.get_weights()
        for name in self.models:
            self.assertAlmostEqual(weights[name], 1.0 / 3.0)

    def test_weight_adaptation(self):
        """Verify that weights adapt correctly based on provided metrics."""
        # "ppo" is doing great, "lstm" is bad
        metrics = {
            "ppo": {"accuracy": 0.9, "calibration_error": 0.0, "drift_score": 0.0},
            "lstm": {"accuracy": 0.1, "calibration_error": 0.5, "drift_score": 0.5},
            "transformer": {"accuracy": 0.5, "calibration_error": 0.1, "drift_score": 0.1},
        }
        initial_weights = self.ensemble.get_weights().copy()

        # Multiple updates to see movement towards target
        for _ in range(5):
            new_weights = self.ensemble.update_weights(metrics)

        self.assertGreater(new_weights["ppo"], initial_weights["ppo"])
        self.assertLess(new_weights["lstm"], initial_weights["lstm"])

    def test_volatility_impact(self):
        """Verify that high volatility increases calibration penalty."""
        metrics = {
            "ppo": {"accuracy": 0.8, "calibration_error": 0.8, "drift_score": 0.0},
            "lstm": {"accuracy": 0.5, "calibration_error": 0.0, "drift_score": 0.0},
            "transformer": {"accuracy": 0.5, "calibration_error": 0.0, "drift_score": 0.0},
        }
        # Low volatility: standard calibration penalty
        regime_low = RegimeInfo(
            label=MarketRegime.UNKNOWN, confidence=1.0, transition_score=0.0, volatility_index=0.5
        )

        for _ in range(10):
            self.ensemble.update_weights(metrics, regime_info=regime_low)
        w_low = self.ensemble.get_weights()["ppo"]

        # Reset weights
        self.ensemble.weights = dict.fromkeys(self.models, 1.0 / 3.0)
        self.ensemble._target_weights = self.ensemble.weights.copy()
        self.ensemble._prev_target_weights = self.ensemble.weights.copy()

        # High volatility: calibration error has severe penalty
        regime_high = RegimeInfo(
            label=MarketRegime.UNKNOWN, confidence=1.0, transition_score=0.0, volatility_index=5.0
        )
        for _ in range(10):
            self.ensemble.update_weights(metrics, regime_info=regime_high)
        w_high = self.ensemble.get_weights()["ppo"]

        self.assertLess(w_high, w_low)

    def test_swing_cap(self):
        """Verify that weight changes are capped by max_swing."""
        metrics = {
            "ppo": {"accuracy": 1.0},
            "lstm": {"accuracy": 0.0},
            "transformer": {"accuracy": 0.0},
        }
        current_ppo_weight = self.ensemble.weights["ppo"]
        new_weights = self.ensemble.update_weights(metrics)

        # Max swing is 0.1, so it shouldn't jump more than ~0.1
        self.assertLessEqual(new_weights["ppo"], current_ppo_weight + 0.11)

    def test_oscillation_dampening(self):
        """Verify that rapid target reversals trigger adaptation dampening."""
        metrics_a = {"ppo": {"accuracy": 1.0}, "lstm": {"accuracy": 0.0}}
        metrics_b = {"ppo": {"accuracy": 0.0}, "lstm": {"accuracy": 1.0}}

        self.ensemble.update_weights(metrics_a)  # Move towards ppo
        w1 = self.ensemble.weights["ppo"]

        self.ensemble.update_weights(metrics_b)  # Move away from ppo
        w2 = self.ensemble.weights["ppo"]

        self.ensemble.update_weights(metrics_a)  # Move back towards ppo (reversal detected)
        w3 = self.ensemble.weights["ppo"]

        step1 = abs(w1 - (1.0 / 3.0))
        step3 = abs(w3 - w2)

        # Step size during oscillation should be much smaller
        self.assertLess(step3, step1)

    def test_autonomous_tracking(self):
        """Verify that internal performance tracking works correctly."""
        # 4 correct, 1 incorrect
        for _ in range(4):
            self.ensemble.record_prediction("ppo", SignalDirection.BUY, 0.9)
            self.ensemble.record_outcome("ppo", SignalDirection.BUY)
        self.ensemble.record_prediction("ppo", SignalDirection.BUY, 0.9)
        self.ensemble.record_outcome("ppo", SignalDirection.SELL)

        metrics = self.ensemble.calculate_metrics("ppo")
        self.assertAlmostEqual(metrics["accuracy"], 0.8)
        # Brier Score: (4 * (0.9-1)^2 + 1 * (0.9-0)^2) / 5 = (4*0.01 + 0.81) / 5 = 0.85 / 5 = 0.17
        self.assertAlmostEqual(metrics["calibration_error"], 0.17)

    def test_drift_detection(self):
        """Verify that recent performance drops trigger high drift scores."""
        # Long-term stable
        for _ in range(20):
            self.ensemble.record_prediction("ppo", SignalDirection.BUY, 1.0)
            self.ensemble.record_outcome("ppo", SignalDirection.BUY)

        # Recent failure (last 4 items in 24 total history -> 1/6th)
        for _ in range(4):
            self.ensemble.record_prediction("ppo", SignalDirection.BUY, 1.0)
            self.ensemble.record_outcome("ppo", SignalDirection.SELL)

        metrics = self.ensemble.calculate_metrics("ppo")
        self.assertGreater(metrics["drift_score"], 0.5)

    def test_min_weight_floor(self):
        """Verify that no model drops below the min_weight floor."""
        metrics = {"ppo": {"accuracy": 1.0}, "lstm": {"accuracy": 0.0}}
        for _ in range(50):
            weights = self.ensemble.update_weights(metrics)

        for name in self.models:
            self.assertGreaterEqual(weights[name], self.ensemble.min_weight - 1e-7)

    def test_regime_aware_alpha(self):
        """Verify that adaptation speed changes based on market regime."""
        metrics = {"ppo": {"accuracy": 1.0}}

        # Trending: Faster adaptation
        regime_trending = RegimeInfo(label=MarketRegime.TRENDING, confidence=1.0, transition_score=0.0, volatility_index=1.0)
        self.ensemble.update_weights(metrics, regime_info=regime_trending)
        step_trending = self.ensemble.weights["ppo"] - (1.0/3.0)

        # Reset
        self.ensemble.weights = dict.fromkeys(self.models, 1.0/3.0)
        self.ensemble._target_weights = self.ensemble.weights.copy()

        # News Shock: Slower adaptation
        regime_news = RegimeInfo(label=MarketRegime.NEWS_SHOCK, confidence=1.0, transition_score=0.0, volatility_index=1.0)
        self.ensemble.update_weights(metrics, regime_info=regime_news)
        step_news = self.ensemble.weights["ppo"] - (1.0/3.0)

        self.assertGreater(step_trending, step_news)


if __name__ == "__main__":
    unittest.main()
