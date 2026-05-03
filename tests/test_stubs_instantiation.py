import numpy as np
import pandas as pd
from src.models.ppo_agent import PPOAgent
from src.models.lstm_model import LSTMModel
from src.models.dreamer_agent import DreamerAgent
from src.trading.trading_env import TradingEnv
from src.models.base_model import Signal
from src.core.constants import SignalDirection

def test_instantiation():
    print("Testing instantiation...")

    # Test TradingEnv
    df = pd.DataFrame(np.random.randn(100, 10), columns=[f"feat_{i}" for i in range(10)])
    env = TradingEnv(df=df, window_size=10)
    obs, info = env.reset()
    assert obs.shape == (10, 10)
    print("TradingEnv OK")

    # Test PPOAgent (should handle missing SB3 gracefully)
    ppo = PPOAgent(env=env)
    sig = ppo.predict(obs)
    assert isinstance(sig, Signal)
    print(f"PPOAgent predict (no SB3): {sig.direction}")

    # Test LSTMModel (should handle missing Torch gracefully)
    lstm = LSTMModel(input_dim=10)
    sig = lstm.predict(obs)
    assert isinstance(sig, Signal)
    print(f"LSTMModel predict (no Torch): {sig.direction}")

    # Test DreamerAgent
    dreamer = DreamerAgent()
    sig = dreamer.predict(obs)
    assert isinstance(sig, Signal)
    assert sig.direction == SignalDirection.HOLD
    print("DreamerAgent OK")

if __name__ == "__main__":
    try:
        test_instantiation()
        print("All instantiation tests passed!")
    except Exception as e:
        print(f"Tests failed: {e}")
        exit(1)
