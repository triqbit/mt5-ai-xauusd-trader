import unittest
import numpy as np
from src.models import BaseModel, Signal, PPOAgent, LSTMModel, DreamerAgent
from src.trading.trading_env import XAUUSDTradingEnv

class TestModelStubs(unittest.TestCase):
    def test_imports(self):
        """Verify that all models can be imported."""
        self.assertIsNotNone(BaseModel)
        self.assertIsNotNone(Signal)
        self.assertIsNotNone(PPOAgent)
        self.assertIsNotNone(LSTMModel)
        self.assertIsNotNone(DreamerAgent)

    def test_dreamer_stub(self):
        """Verify DreamerAgent stub."""
        agent = DreamerAgent()
        features = np.zeros((60, 140))
        signal = agent.predict(features)
        self.assertIsInstance(signal, Signal)
        self.assertEqual(signal.direction, 0)
        self.assertEqual(signal.confidence, 0.0)

    def test_lstm_stub(self):
        """Verify LSTMModel stub."""
        model = LSTMModel(input_dim=10)
        features = np.zeros((60, 10))
        signal = model.predict(features)
        self.assertIsInstance(signal, Signal)
        self.assertIn(signal.direction, [-1, 0, 1])
        self.assertGreaterEqual(signal.confidence, 0.0)

    def test_env_init(self):
        """Verify XAUUSDTradingEnv initialization."""
        data = np.zeros((100, 10))
        env = XAUUSDTradingEnv(data=data)
        if hasattr(env, 'observation_space'):
            self.assertIsNotNone(env.observation_space)
            self.assertIsNotNone(env.action_space)

if __name__ == "__main__":
    unittest.main()
