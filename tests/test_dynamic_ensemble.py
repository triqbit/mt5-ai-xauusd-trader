import unittest

from src.core.constants import SignalDirection
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

    def test_volatility_scoring_threshold(self):
        """Verify the 2.0 volatility threshold for extra calibration penalty."""
        # Model with high calibration error
        metrics = {"ppo": {"accuracy": 0.5, "calibration_error": 1.0}}

        # 1. Volatility = 1.9 (No extra penalty)
        regime_low = RegimeInfo(
            label=MarketRegime.UNKNOWN, confidence=1.0, transition_score=0.0, volatility_index=1.9
        )
        self.ensemble.update_weights(metrics, regime_info=regime_low)
        w_low = self.ensemble.weights["ppo"]

        # Reset
        self.ensemble.weights = dict.fromkeys(self.models, 1.0 / 3.0)
        self.ensemble._target_weights = self.ensemble.weights.copy()

        # 2. Volatility = 2.1 (Extra penalty)
        regime_high = RegimeInfo(
            label=MarketRegime.UNKNOWN, confidence=1.0, transition_score=0.0, volatility_index=2.1
        )
        self.ensemble.update_weights(metrics, regime_info=regime_high)
        w_high = self.ensemble.weights["ppo"]

        # w_high should be lower than w_low because of the extra -0.3 * cal penalty
        self.assertLess(w_high, w_low)

    def test_explicit_volatility_context(self):
        """Verify that volatility_context override works and slows down adaptation."""
        metrics = {
            "ppo": {"accuracy": 1.0, "calibration_error": 0.0, "drift_score": 0.0},
            "lstm": {"accuracy": 0.0, "calibration_error": 0.0, "drift_score": 0.0},
            "transformer": {"accuracy": 0.0, "calibration_error": 0.0, "drift_score": 0.0},
        }
        initial_ppo = self.ensemble.weights["ppo"]

        # 1. Update with low volatility context
        self.ensemble.update_weights(metrics, volatility_context=0.5)
        w_low_vol = self.ensemble.weights["ppo"]
        step_low = w_low_vol - initial_ppo

        # Reset
        self.ensemble.weights = dict.fromkeys(self.models, 1.0 / 3.0)
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
            label=MarketRegime.VOLATILE_BREAKOUT,
            confidence=1.0,
            transition_score=0.0,
            volatility_index=1.0,
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
            label=MarketRegime.MEAN_REVERSION,
            confidence=1.0,
            transition_score=0.0,
            volatility_index=1.0,
        )

        for _ in range(10):
            weights = self.ensemble.update_weights(metrics, regime_info=regime_mean_rev)

        self.assertGreater(weights["lstm"], weights["ppo"])

    def test_regime_alpha_scaling(self):
        """Verify that regime-aware alpha adjustments are correctly applied."""
        # Use lower smoothing to avoid hitting max_swing cap in both cases
        ensemble = DynamicEnsemble(model_names=self.models, smoothing_factor=0.05, max_swing=0.1)
        metrics = {
            "ppo": {"accuracy": 1.0, "calibration_error": 0.0, "drift_score": 0.0},
            "lstm": {"accuracy": 0.0, "calibration_error": 0.0, "drift_score": 0.0},
            "transformer": {"accuracy": 0.0, "calibration_error": 0.0, "drift_score": 0.0},
        }

        # Test TRENDING (Alpha increased: 1.2x)
        regime_trending = RegimeInfo(
            label=MarketRegime.TRENDING, confidence=1.0, transition_score=0.0, volatility_index=1.0
        )
        ensemble.update_weights(metrics, regime_info=regime_trending)
        w_trending = ensemble.weights["ppo"]
        step_trending = w_trending - (1.0 / 3.0)

        # Reset
        ensemble.weights = dict.fromkeys(self.models, 1.0 / 3.0)
        ensemble._target_weights = ensemble.weights.copy()

        # Test NEWS_SHOCK (Alpha decreased: 0.5x)
        regime_news = RegimeInfo(
            label=MarketRegime.NEWS_SHOCK,
            confidence=1.0,
            transition_score=0.0,
            volatility_index=1.0,
        )
        ensemble.update_weights(metrics, regime_info=regime_news)
        w_news = ensemble.weights["ppo"]
        step_news = w_news - (1.0 / 3.0)

        self.assertGreater(step_trending, step_news)

    def test_news_shock_alpha_halving(self):
        """Verify that NEWS_SHOCK specifically halves the adaptation rate."""
        metrics = {"ppo": {"accuracy": 1.0}}

        # UNKNOWN regime, vol=1.0 -> alpha = smoothing_factor * (2/(1+1)) = smoothing_factor
        regime_normal = RegimeInfo(
            label=MarketRegime.UNKNOWN, confidence=1.0, transition_score=0.0, volatility_index=1.0
        )
        self.ensemble.update_weights(metrics, regime_info=regime_normal)
        step_normal = self.ensemble.weights["ppo"] - (1.0 / 3.0)

        # Reset
        self.ensemble.weights = dict.fromkeys(self.models, 1.0 / 3.0)
        self.ensemble._target_weights = self.ensemble.weights.copy()

        # NEWS_SHOCK regime, vol=1.0 -> alpha = smoothing_factor * 0.5
        regime_news = RegimeInfo(
            label=MarketRegime.NEWS_SHOCK,
            confidence=1.0,
            transition_score=0.0,
            volatility_index=1.0,
        )
        self.ensemble.update_weights(metrics, regime_info=regime_news)
        step_news = self.ensemble.weights["ppo"] - (1.0 / 3.0)

        # Should be exactly half (allowing for floating point)
        self.assertAlmostEqual(step_news, step_normal * 0.5, places=5)

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
        ensemble = DynamicEnsemble(
            model_names=self.models, min_weight=0.05, initial_weights=initial
        )
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

    def test_autonomous_tracking(self):
        """Verify that record_prediction and record_outcome correctly populate history."""
        self.ensemble.record_prediction("ppo", SignalDirection.BUY, 0.8)
        self.ensemble.record_outcome("ppo", SignalDirection.BUY)

        history = self.ensemble._history["ppo"]
        self.assertEqual(len(history), 1)
        self.assertTrue(history[0]["correct"])
        self.assertEqual(history[0]["accuracy_gain"], 1.0)
        # Brier score = (0.8 - 1.0)**2 = 0.04
        self.assertAlmostEqual(history[0]["calibration_error"], 0.04)

    def test_calculate_metrics(self):
        """Verify calculate_metrics returns expected values."""
        # 4 correct, 1 incorrect. Confidence always 1.0.
        for _ in range(4):
            self.ensemble.record_prediction("ppo", SignalDirection.BUY, 1.0)
            self.ensemble.record_outcome("ppo", SignalDirection.BUY)
        self.ensemble.record_prediction("ppo", SignalDirection.BUY, 1.0)
        self.ensemble.record_outcome("ppo", SignalDirection.SELL)

        metrics = self.ensemble.calculate_metrics("ppo")
        self.assertAlmostEqual(metrics["accuracy"], 0.8)
        # Brier scores: 4 * (1-1)^2 + 1 * (1-0)^2 = 1.0
        # Avg = 1.0 / 5 = 0.2
        self.assertAlmostEqual(metrics["calibration_error"], 0.2)

    def test_drift_detection(self):
        """Verify drift_score calculation (recent performance drop)."""
        # Long-term: 10 correct
        for _ in range(10):
            self.ensemble.record_prediction("ppo", SignalDirection.BUY, 1.0)
            self.ensemble.record_outcome("ppo", SignalDirection.BUY)

        # Recent: 5 incorrect
        for _ in range(5):
            self.ensemble.record_prediction("ppo", SignalDirection.BUY, 1.0)
            self.ensemble.record_outcome("ppo", SignalDirection.SELL)

        metrics = self.ensemble.calculate_metrics("ppo")
        # acc = 10/15 = 0.66
        # recent_acc (last 3 because 15//5=3) = 0/3 = 0.0
        # drift = (0.66 - 0.0) * 2 = 1.32 -> capped at 1.0
        self.assertAlmostEqual(metrics["drift_score"], 1.0)

    def test_update_weights_autonomous(self):
        """Verify update_weights works using internal history only."""
        # PPO perfect, LSTM failing
        for _ in range(10):
            self.ensemble.record_prediction("ppo", SignalDirection.BUY, 1.0)
            self.ensemble.record_outcome("ppo", SignalDirection.BUY)
            self.ensemble.record_prediction("lstm", SignalDirection.BUY, 1.0)
            self.ensemble.record_outcome("lstm", SignalDirection.SELL)

        initial_weights = self.ensemble.get_weights()
        new_weights = self.ensemble.update_weights()  # No metrics passed

        self.assertGreater(new_weights["ppo"], initial_weights["ppo"])
        self.assertLess(new_weights["lstm"], initial_weights["lstm"])

    def test_metric_blending(self):
        """Verify external metrics override internal ones."""
        # Internally PPO is perfect
        self.ensemble.record_prediction("ppo", SignalDirection.BUY, 1.0)
        self.ensemble.record_outcome("ppo", SignalDirection.BUY)

        # Externally PPO is terrible
        external_metrics = {"ppo": {"accuracy": 0.0, "calibration_error": 1.0, "drift_score": 1.0}}

        initial_ppo = self.ensemble.weights["ppo"]
        # If external overrides, PPO weight should drop
        new_weights = self.ensemble.update_weights(metrics=external_metrics)

        self.assertLess(new_weights["ppo"], initial_ppo)

    def test_brier_score_calibration(self):
        """Verify that calibration error uses Brier Score (squared error)."""
        # Prediction confidence 0.8, outcome correct (1.0)
        # Brier score = (0.8 - 1.0)**2 = 0.04
        self.ensemble.record_prediction("ppo", SignalDirection.BUY, 0.8)
        self.ensemble.record_outcome("ppo", SignalDirection.BUY)

        metrics = self.ensemble.calculate_metrics("ppo")
        self.assertAlmostEqual(metrics["calibration_error"], 0.04)

        # Prediction confidence 0.8, outcome incorrect (0.0)
        # Brier score = (0.8 - 0.0)**2 = 0.64
        # Avg = (0.04 + 0.64) / 2 = 0.34
        self.ensemble.record_prediction("lstm", SignalDirection.BUY, 0.8)
        self.ensemble.record_outcome("lstm", SignalDirection.SELL)

        metrics = self.ensemble.calculate_metrics("lstm")
        self.assertAlmostEqual(metrics["calibration_error"], 0.64)

    def test_sensitivity_ratio_drift(self):
        """Verify drift_score calculation using sensitivity-ratio approach."""
        # Sensitivity-ratio: (acc - recent_acc) / (acc + 1e-9) * 2.0

        # Window: 10 predictions
        # 8 correct in first 8
        for _ in range(8):
            self.ensemble.record_prediction("ppo", SignalDirection.BUY, 1.0)
            self.ensemble.record_outcome("ppo", SignalDirection.BUY)

        # 2 incorrect in last 2 (recent 20%)
        for _ in range(2):
            self.ensemble.record_prediction("ppo", SignalDirection.BUY, 1.0)
            self.ensemble.record_outcome("ppo", SignalDirection.SELL)

        # Total acc = 8/10 = 0.8
        # Recent acc (last 2) = 0/2 = 0.0
        # Drift = (0.8 - 0.0) / (0.8 + 1e-9) * 2.0 = 2.0 -> capped at 1.0
        metrics = self.ensemble.calculate_metrics("ppo")
        self.assertEqual(metrics["drift_score"], 1.0)

        # Let's try a less extreme case
        # Try:
        # First 8: 8 correct.
        # Last 2: 1 correct.
        # Total acc = 9/10 = 0.9
        # Recent acc = 1/2 = 0.5
        # Drift = (0.9 - 0.5) / (0.9 + 1e-9) * 2.0 = 0.4 / 0.9 * 2 = 0.888...
        self.ensemble._history["transformer"].clear()
        for _ in range(8):
            self.ensemble.record_prediction("transformer", SignalDirection.BUY, 1.0)
            self.ensemble.record_outcome("transformer", SignalDirection.BUY)
        for _ in range(1):
            self.ensemble.record_prediction("transformer", SignalDirection.BUY, 1.0)
            self.ensemble.record_outcome("transformer", SignalDirection.BUY)
        for _ in range(1):
            self.ensemble.record_prediction("transformer", SignalDirection.BUY, 1.0)
            self.ensemble.record_outcome("transformer", SignalDirection.SELL)

        metrics = self.ensemble.calculate_metrics("transformer")
        # Accuracy drift = 0.888...
        # Calibration drift = 0.0 (error is perfect then 0.0 or 1.0 but small average)
        # We just want to check it's non-zero and roughly aligned with blended formula
        self.assertGreater(metrics["drift_score"], 0.0)

    def test_calibration_drift_detection(self):
        """Verify calibration_drift calculation (reliability decay)."""
        # Long-term: low calibration error (perfect confidence)
        for _ in range(8):
            self.ensemble.record_prediction("ppo", SignalDirection.BUY, 1.0)
            self.ensemble.record_outcome("ppo", SignalDirection.BUY)

        # Recent: high calibration error (miscalibrated confidence)
        # Prediction 0.5, Outcome 1.0 -> Error 0.25
        for _ in range(2):
            self.ensemble.record_prediction("ppo", SignalDirection.BUY, 0.5)
            self.ensemble.record_outcome("ppo", SignalDirection.BUY)

        metrics = self.ensemble.calculate_metrics("ppo")
        # acc_drift = 0.0 (all correct)
        # cal_drift = (recent_cal - cal) / cal * 2.0
        # cal = (8*0 + 2*0.25) / 10 = 0.05
        # recent_cal = 0.25
        # cal_drift = (0.25 - 0.05) / 0.05 * 2.0 = 4.0 -> capped at 1.0
        # blended drift = 0.7*0 + 0.3*1.0 = 0.3
        self.assertAlmostEqual(metrics["drift_score"], 0.3)

    def test_high_volatility_drift_penalty(self):
        """Verify that drift_penalty increases in high-volatility contexts."""
        # Setup model with drift
        metrics = {
            "ppo": {"accuracy": 0.5, "calibration_error": 0.0, "drift_score": 1.0},
            "lstm": {"accuracy": 0.5, "calibration_error": 0.0, "drift_score": 0.0},
            "transformer": {"accuracy": 0.5, "calibration_error": 0.0, "drift_score": 0.0},
        }

        # 1. Low Volatility (vol=1.0)
        # Score = 0.5 - 0.3*0 - 0.4*1.0 = 0.1
        regime_low = RegimeInfo(
            label=MarketRegime.UNKNOWN, confidence=1.0, transition_score=0.0, volatility_index=1.0
        )
        for _ in range(10):
            self.ensemble.update_weights(metrics, regime_info=regime_low)
        w_low = self.ensemble.weights["ppo"]

        # Reset
        self.ensemble.weights = dict.fromkeys(self.models, 1.0 / 3.0)
        self.ensemble._target_weights = self.ensemble.weights.copy()
        self.ensemble._prev_target_weights = self.ensemble.weights.copy()

        # 2. High Volatility (vol=3.0)
        # drift_penalty = 0.4 * 1.5 = 0.6
        # Score = 0.5 - 0.3*0 - 0.6*1.0 = -0.1 -> max(score, 0.01) = 0.01
        regime_high = RegimeInfo(
            label=MarketRegime.UNKNOWN, confidence=1.0, transition_score=0.0, volatility_index=3.0
        )
        for _ in range(10):
            self.ensemble.update_weights(metrics, regime_info=regime_high)
        w_high = self.ensemble.weights["ppo"]

        # w_high should be much lower than w_low due to increased penalty
        self.assertLess(w_high, w_low)


if __name__ == "__main__":
    unittest.main()
