import unittest
import numpy as np
from unittest.mock import MagicMock
from src.models.ensemble import EnsembleModel

class TestEnsembleModel(unittest.TestCase):
    def setUp(self):
        self.model = EnsembleModel(device="cpu")

    def test_predict_no_models(self):
        obs = np.random.rand(140)
        direction, confidence, votes = self.model.predict(obs)
        # Should return HOLD (0) with 1.0 confidence because of dreamer mock
        self.assertEqual(direction, 0)
        self.assertEqual(confidence, 1.0)

    def test_rebalance_weights(self):
        # Initial weights 1/3
        self.model.record_return("ppo", 0.01)
        self.model.record_return("lstm", -0.01)
        # Need 50 returns to trigger rebalance
        for _ in range(50):
            self.model.record_return("ppo", 0.02)
            self.model.record_return("lstm", 0.01)
            self.model.record_return("dreamer", 0.015)

        self.assertAlmostEqual(sum(self.model.weights.values()), 1.0)
        # PPO should have highest weight
        self.assertTrue(self.model.weights["ppo"] > self.model.weights["lstm"])

if __name__ == "__main__":
    unittest.main()
