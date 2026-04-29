"""src/environment package - Gymnasium trading environment."""

try:
    from .gym_env import TradingEnv
except ImportError:
    TradingEnv = None  # type: ignore

__all__ = ["TradingEnv"]
