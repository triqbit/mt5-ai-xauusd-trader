"""src/environment package - Gymnasium trading environment."""
try:
    from .gym_env import TradingEnv
except ImportError:
    pass

__all__ = ["TradingEnv"]
