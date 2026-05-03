
import numpy as np

from src.environment.gym_env import TradingEnv


def test_observation_consistency():
    # Set seed for reproducibility
    np.random.seed(42)
    n_features = 5
    window_size = 10
    data = np.random.randn(100, n_features).astype(np.float32)
    env = TradingEnv(data, window_size=window_size)

    # Manually calculate expected observation for a few steps
    for step in range(window_size, window_size + 5):
        env.current_step = step
        obs = env._get_observation()

        # Reference calculation (matching current implementation)
        window = data[step - window_size:step]
        expected_normalized = (window - window.mean(axis=0)) / (window.std(axis=0) + 1e-8)
        expected_portfolio = np.array([env.balance / env.initial_balance, env.position], dtype=np.float32)
        expected_obs = np.concatenate([expected_normalized.flatten(), expected_portfolio]).astype(np.float32)

        np.testing.assert_allclose(obs, expected_obs, rtol=1e-5, atol=1e-5)

if __name__ == "__main__":
    test_observation_consistency()
