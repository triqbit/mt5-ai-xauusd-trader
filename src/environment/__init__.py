"""src/environment package - Gymnasium trading environment."""
import contextlib

with contextlib.suppress(ImportError):
    from .gym_env import TradingEnv

__all__ = ["TradingEnv"]
