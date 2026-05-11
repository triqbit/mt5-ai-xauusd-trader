import unittest
import numpy as np
from src.core.constants import SignalDirection
from src.models.ensemble import EnsembleModel
from src.models.regime_detector import MarketRegime, RegimeInfo

class TestEnsembleIntegration(unittest.TestCase):
    def setUp(self):
        self.model = EnsembleModel()
        self.regime_trending = RegimeInfo(
            label=MarketRegime.TRENDING,
            confidence=1.0,
            transition_score=0.0,
            volatility_index=1.0
        )

    def test_observe_outcome_delegation(self):
        """Verify that observe_outcome correctly impacts weights via DynamicEnsemble."""
        # Initial weights should be equal
        initial_weights = self.model.weights.copy()

        # PPO is always right
        for _ in range(10):
            # We must record predictions first because DynamicEnsemble.record_outcome
            # pops from _pending_predictions
            self.model.dynamic_ensemble.record_prediction("ppo", SignalDirection.BUY, 1.0)
            self.model.dynamic_ensemble.record_prediction("dreamer", SignalDirection.SELL, 1.0)
            self.model.dynamic_ensemble.record_prediction("lstm", SignalDirection.SELL, 1.0)

            self.model.observe_outcome(SignalDirection.BUY, regime_info=self.regime_trending)

        new_weights = self.model.weights
        self.assertGreater(new_weights["ppo"], initial_weights["ppo"])
        self.assertLess(new_weights["dreamer"], initial_weights["dreamer"])

if __name__ == "__main__":
    unittest.main()
