import time
import numpy as np
import os
import sys

# Add current dir to path to import src
sys.path.append(os.getcwd())

from src.environment.gym_env import TradingEnv

def benchmark():
    # Generate synthetic data: 10,000 steps, 140 features
    data = np.random.randn(10000, 140).astype(np.float32)
    env = TradingEnv(data, window_size=60)

    start_time = time.time()
    obs, info = env.reset()

    steps = 0
    done = False
    while not done:
        action = 0  # Hold
        obs, reward, terminated, truncated, info = env.step(action)
        steps += 1
        done = terminated or truncated

    end_time = time.time()
    duration = end_time - start_time
    print(f"Total steps: {steps}")
    print(f"Duration: {duration:.4f} seconds")
    print(f"Steps per second: {steps / duration:.2f}")

if __name__ == "__main__":
    benchmark()
