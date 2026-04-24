import unittest
import numpy as np
import torch
from src.models.ensemble import EnsembleModel

class TestEnsembleModel(unittest.TestCase):
    def setUp(self):
        self.ensemble = EnsembleModel(device="cpu")

    def test_predict_no_models(self):
        obs = np.zeros(140)
        direction, confidence, per_algo = self.ensemble.predict(obs)
        self.assertEqual(direction, 0)
        self.assertEqual(confidence, 0.0)
        self.assertEqual(per_algo, {})

    def test_weighted_voting(self):
        # Mock PPO
        ppo_mock = MagicMock()
        ppo_mock.predict.return_value = (1, None) # Buy
        self.ensemble._ppo_model = ppo_mock

        # Give PPO all weight for this test
        self.ensemble.weights = {"ppo": 1.0, "dreamer": 0.0, "lstm": 0.0}

        obs = np.zeros(140)
        direction, confidence, per_algo = self.ensemble.predict(obs)

        self.assertEqual(direction, 1) # Buy
        self.assertEqual(confidence, 1.0)
        self.assertEqual(per_algo["ppo"], 1.0)

    def test_rebalance_weights(self):
        # Initial equal weights
        self.ensemble._performance["ppo"] = [0.1] * 50
        self.ensemble._performance["dreamer"] = [0.01] * 50
        self.ensemble._performance["lstm"] = [-0.05] * 50

        self.ensemble._rebalance_weights()

        # PPO should have highest weight
        self.assertGreater(self.ensemble.weights["ppo"], self.ensemble.weights["dreamer"])
        self.assertGreater(self.ensemble.weights["dreamer"], self.ensemble.weights["lstm"])
        # All weights should sum to 1.0
        self.assertAlmostEqual(sum(self.ensemble.weights.values()), 1.0)

from unittest.mock import MagicMock

if __name__ == "__main__":
    unittest.main()
