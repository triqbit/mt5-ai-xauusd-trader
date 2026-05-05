import unittest

from src.models.dynamic_ensemble import DynamicEnsemble
from src.models.regime_detector import MarketRegime, RegimeInfo


class TestDynamicEnsemble(unittest.TestCase):
    def setUp(self):
        self.models = ["ppo", "lstm", "transformer"]
        self.ensemble = DynamicEnsemble(
            model_names=self.models,
            smoothing_factor=0.5,  # Faster for testing
            max_swing=0.1
        )

    def test_initial_weights(self):
        weights = self.ensemble.get_weights()
        for name in self.models:
            self.assertAlmostEqual(weights[name], 1.0/3.0)

    def test_weight_adaptation(self):
        # "ppo" is doing great, "lstm" is bad
        metrics = {
            "ppo": {"accuracy": 0.9, "calibration_error": 0.0, "drift_score": 0.0},
            "lstm": {"accuracy": 0.1, "calibration_error": 0.5, "drift_score": 0.5},
            "transformer": {"accuracy": 0.5, "calibration_error": 0.1, "drift_score": 0.1}
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
            "transformer": {"accuracy": 0.5, "calibration_error": 0.0, "drift_score": 0.0}
        }
        # Use UNKNOWN regime to isolate volatility impact
        # Low volatility: calibration error has NO extra penalty
        regime_low = RegimeInfo(label=MarketRegime.UNKNOWN, confidence=1.0, transition_score=0.0, volatility_index=0.5)

        # Run multiple updates to reach steady state
        for _ in range(10):
            self.ensemble.update_weights(metrics, regime_info=regime_low)
        w_low = self.ensemble.get_weights()["ppo"]

        # Reset weights
        self.ensemble.weights = dict.fromkeys(self.models, 1.0/3.0)
        self.ensemble._target_weights = self.ensemble.weights.copy()
        self.ensemble._prev_target_weights = self.ensemble.weights.copy()

        # High volatility: calibration error has severe penalty (score -= 0.3 * cal)
        regime_high = RegimeInfo(label=MarketRegime.UNKNOWN, confidence=1.0, transition_score=0.0, volatility_index=5.0)
        for _ in range(10):
            self.ensemble.update_weights(metrics, regime_info=regime_high)
        w_high = self.ensemble.get_weights()["ppo"]

        self.assertLess(w_high, w_low)

    def test_explicit_volatility_context(self):
        """Verify that volatility_context override works and slows down adaptation."""
        metrics = {
            "ppo": {"accuracy": 1.0, "calibration_error": 0.0, "drift_score": 0.0},
            "lstm": {"accuracy": 0.0, "calibration_error": 0.0, "drift_score": 0.0},
            "transformer": {"accuracy": 0.0, "calibration_error": 0.0, "drift_score": 0.0}
        }
        initial_ppo = self.ensemble.weights["ppo"]

        # 1. Update with low volatility context
        self.ensemble.update_weights(metrics, volatility_context=0.5)
        w_low_vol = self.ensemble.weights["ppo"]
        step_low = w_low_vol - initial_ppo

        # Reset
        self.ensemble.weights = dict.fromkeys(self.models, 1.0/3.0)
        self.ensemble._target_weights = self.ensemble.weights.copy()
        self.ensemble._prev_target_weights = self.ensemble.weights.copy()

        # 2. Update with high volatility context
        self.ensemble.update_weights(metrics, volatility_context=10.0)
        w_high_vol = self.ensemble.weights["ppo"]
        step_high = w_high_vol - initial_ppo

        # Step size in high vol should be much smaller than in low vol due to vol_factor scaling alpha
        self.assertLess(step_high, step_low)

    def test_swing_cap(self):
        # Extreme change in metrics
        metrics = {
            "ppo": {"accuracy": 1.0},
            "lstm": {"accuracy": 0.0},
            "transformer": {"accuracy": 0.0}
        }
        current_ppo_weight = self.ensemble.weights["ppo"]
        new_weights = self.ensemble.update_weights(metrics)

        # Max swing is 0.1, so it shouldn't jump to 1.0 immediately
        self.assertLessEqual(new_weights["ppo"], current_ppo_weight + 0.11)

    def test_oscillation_dampening(self):
        # Force target to flip-flop
        metrics_a = {"ppo": {"accuracy": 1.0}, "lstm": {"accuracy": 0.0}, "transformer": {"accuracy": 0.0}}
        metrics_b = {"ppo": {"accuracy": 0.0}, "lstm": {"accuracy": 1.0}, "transformer": {"accuracy": 0.0}}

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
            "transformer": {"accuracy": 0.0}
        }
        for _ in range(20):
            weights = self.ensemble.update_weights(metrics)

        for name in self.models:
            self.assertGreaterEqual(weights[name], self.ensemble.min_weight - 1e-6)

    def test_regime_scoring_trending(self):
        # In TRENDING regime, low drift should be favored.
        # "ppo" has high drift, "lstm" has low drift.
        metrics = {
            "ppo": {"accuracy": 0.5, "calibration_error": 0.0, "drift_score": 1.0},
            "lstm": {"accuracy": 0.5, "calibration_error": 0.0, "drift_score": 0.0},
            "transformer": {"accuracy": 0.5, "calibration_error": 0.0, "drift_score": 0.5},
        }
        regime_trending = RegimeInfo(
            label=MarketRegime.TRENDING, confidence=1.0, transition_score=0.0, volatility_index=1.0
        )

        for _ in range(10):
            weights = self.ensemble.update_weights(metrics, regime_info=regime_trending)

        self.assertGreater(weights["lstm"], weights["ppo"])

    def test_regime_scoring_volatile_breakout(self):
        # In VOLATILE_BREAKOUT regime, low calibration error should be favored.
        # "ppo" has high calibration error, "lstm" has low calibration error.
        metrics = {
            "ppo": {"accuracy": 0.5, "calibration_error": 1.0, "drift_score": 0.0},
            "lstm": {"accuracy": 0.5, "calibration_error": 0.0, "drift_score": 0.0},
            "transformer": {"accuracy": 0.5, "calibration_error": 0.5, "drift_score": 0.0},
        }
        regime_breakout = RegimeInfo(
            label=MarketRegime.VOLATILE_BREAKOUT, confidence=1.0, transition_score=0.0, volatility_index=1.0
        )

        for _ in range(10):
            weights = self.ensemble.update_weights(metrics, regime_info=regime_breakout)

        self.assertGreater(weights["lstm"], weights["ppo"])

    def test_regime_scoring_mean_reversion(self):
        # In MEAN_REVERSION regime, overconfidence (high calibration error) is penalized even more severely.
        metrics = {
            "ppo": {"accuracy": 0.5, "calibration_error": 1.0, "drift_score": 0.0},
            "lstm": {"accuracy": 0.5, "calibration_error": 0.0, "drift_score": 0.0},
            "transformer": {"accuracy": 0.5, "calibration_error": 0.5, "drift_score": 0.0},
        }
        regime_mean_rev = RegimeInfo(
            label=MarketRegime.MEAN_REVERSION, confidence=1.0, transition_score=0.0, volatility_index=1.0
        )

        for _ in range(10):
            weights = self.ensemble.update_weights(metrics, regime_info=regime_mean_rev)

        self.assertGreater(weights["lstm"], weights["ppo"])

    def test_ema_decay_logic(self):
        # Verify that weights move towards the target incrementally (EMA decay)
        # Target: ppo=1.0, others=0.0
        metrics = {
            "ppo": {"accuracy": 1.0, "calibration_error": 0.0, "drift_score": 0.0},
            "lstm": {"accuracy": 0.0, "calibration_error": 0.0, "drift_score": 0.0},
            "transformer": {"accuracy": 0.0, "calibration_error": 0.0, "drift_score": 0.0},
        }

        initial_ppo = self.ensemble.weights["ppo"]

        # First update
        self.ensemble.update_weights(metrics)
        w1 = self.ensemble.weights["ppo"]

        # Second update
        self.ensemble.update_weights(metrics)
        w2 = self.ensemble.weights["ppo"]

        # Weights should be increasing towards target 1.0
        self.assertGreater(w1, initial_ppo)
        self.assertGreater(w2, w1)
        # But it shouldn't jump to the target (0.9+) immediately due to smoothing (EMA) and swing cap
        self.assertLess(w2, 0.8)

    def test_initial_weights_custom(self):
        initial = {"ppo": 0.6, "lstm": 0.2, "transformer": 0.2}
        ensemble = DynamicEnsemble(model_names=self.models, initial_weights=initial)
        weights = ensemble.get_weights()
        for name in self.models:
            self.assertAlmostEqual(weights[name], initial[name])

    def test_initial_weights_normalization(self):
        initial = {"ppo": 6.0, "lstm": 2.0, "transformer": 2.0}
        ensemble = DynamicEnsemble(model_names=self.models, initial_weights=initial)
        weights = ensemble.get_weights()
        self.assertAlmostEqual(weights["ppo"], 0.6)
        self.assertAlmostEqual(weights["lstm"], 0.2)
        self.assertAlmostEqual(weights["transformer"], 0.2)

    def test_initial_weights_min_respect(self):
        initial = {"ppo": 0.98, "lstm": 0.01, "transformer": 0.01}
        # min_weight=0.05
        ensemble = DynamicEnsemble(model_names=self.models, min_weight=0.05, initial_weights=initial)
        weights = ensemble.get_weights()
        self.assertGreaterEqual(weights["lstm"], 0.05)
        self.assertGreaterEqual(weights["transformer"], 0.05)
        self.assertAlmostEqual(sum(weights.values()), 1.0)

    def test_input_validation(self):
        with self.assertRaises(ValueError):
            DynamicEnsemble(model_names=[], smoothing_factor=0.1)
        with self.assertRaises(ValueError):
            DynamicEnsemble(model_names=self.models, smoothing_factor=-0.1)
        with self.assertRaises(ValueError):
            DynamicEnsemble(model_names=self.models, smoothing_factor=1.1)
        with self.assertRaises(ValueError):
            DynamicEnsemble(model_names=self.models, max_swing=0.0)
        with self.assertRaises(ValueError):
            DynamicEnsemble(model_names=self.models, min_weight=-0.1)
        with self.assertRaises(ValueError):
            DynamicEnsemble(model_names=self.models, min_weight=0.4)  # 3 * 0.4 = 1.2 > 1.0

if __name__ == '__main__':
    unittest.main()
