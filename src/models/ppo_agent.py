"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/ppo_agent.py
Proximal Policy Optimization (PPO) agent using Stable-Baselines3.
Wraps the PPO algorithm for use with the custom Gymnasium trading environment.
"""

import logging
from pathlib import Path
from typing import Optional

from stable_baselines3 import PPO
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.vec_env import DummyVecEnv


class PPOAgent:
    """
    PPO-based reinforcement learning agent.
    Uses Stable-Baselines3 PPO under the hood.
    """
    def __init__(self, env, model_path: Optional[Path] = None, device: str = "auto"):
        from stable_baselines3 import PPO
        from stable_baselines3.common.vec_env import DummyVecEnv

        self.logger = logging.getLogger(__name__)
        self.device = device
        self.env = DummyVecEnv([lambda: env])

        if model_path and Path(model_path).exists():
            self.logger.info(f"Loading existing PPO model from {model_path}")
            self.model = PPO.load(model_path, env=self.env, device=device)
        else:
            self.logger.info("Creating new PPO model...")
            self.model = PPO(
                policy="MlpPolicy",
                env=self.env,
                learning_rate=3e-4,
                n_steps=2048,
                batch_size=64,
                n_epochs=10,
                gamma=0.99,
                gae_lambda=0.95,
                clip_range=0.2,
                ent_coef=0.01,
                vf_coef=0.5,
                max_grad_norm=0.5,
                verbose=1,
                device=device,
            )

    def train(self, total_timesteps: int = 1_000_000, save_path: Optional[Path] = None):
        """Train the PPO agent."""
        self.logger.info(f"Starting PPO training for {total_timesteps} timesteps...")
        self.model.learn(total_timesteps=total_timesteps)

        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            self.model.save(save_path)
            self.logger.info(f"Model saved to {save_path}")

    def predict(self, observation):
        """Generate a trading action from the current observation."""
        action, _states = self.model.predict(observation, deterministic=True)
        return action

    def evaluate(self, n_eval_episodes: int = 10) -> dict:
        """Evaluate agent performance over n episodes."""
        from stable_baselines3.common.evaluation import evaluate_policy
        mean_reward, std_reward = evaluate_policy(
            self.model, self.env, n_eval_episodes=n_eval_episodes
        )
        return {"mean_reward": mean_reward, "std_reward": std_reward}
