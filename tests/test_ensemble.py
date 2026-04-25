import unittest
from unittest.mock import MagicMock
import numpy as np
from src.models.ensemble import EnsembleModel

# Conditional import for torch to support CI environments without it
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

class TestEnsembleModel(unittest.TestCase):
    def setUp(self):
        self.model = EnsembleModel(device="cpu")

    def test_predict_no_models(self):
        obs = np.random.rand(140)
        direction, confidence, per_algo = self.model.predict(obs)
        self.assertEqual(direction, 0)
        self.assertEqual(confidence, 0.0)

    @unittest.skipUnless(TORCH_AVAILABLE, "torch not available")
    def test_weighted_voting_logic(self):
        # Set specific weights
        self.model.weights = {"ppo": 0.7, "lstm": 0.3}

        # Mock models
        self.model._ppo_model = MagicMock()
        # Mapping: 0=Hold, 1=Buy, 2=Sell
        self.model._ppo_model.predict.return_value = (1, None) # Buy

        self.model.lstm_model = MagicMock()
        # Mock LSTM logits [Hold, Buy, Sell]
        # We want LSTM to vote Sell (2)
        # Logits: [0, 0, 10] -> Probabilities: [~0, ~0, 1]
        self.model.lstm_model.return_value = torch.tensor([[0.0, 0.0, 10.0]])

        obs = np.random.rand(140)
        seq = torch.randn(10, 140)

        direction, confidence, per_algo = self.model.predict(obs, seq=seq)

        # PPO: Buy (1) -> [0, 1, 0] * 0.7 = [0, 0.7, 0]
        # LSTM: Sell (2) -> [0, 0, 1] * 0.3 = [0, 0, 0.3]
        # Blended: [0, 0.7, 0.3]
        # Argmax is 1 (Buy)
        # Confidence is 0.7

        self.assertEqual(direction, 1)
        self.assertAlmostEqual(confidence, 0.7, places=4)
        self.assertEqual(per_algo["ppo"], 1.0)
        self.assertEqual(per_algo["lstm"], 2.0)

if __name__ == "__main__":
    unittest.main()
