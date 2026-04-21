"""src/environment package - Gymnasium trading environment."""

try:
    from .gym_env import TradingEnv
except ImportError:
    # Heavy dependencies (gymnasium) might be missing in CI environment
    TradingEnv = None  # type: ignore

__all__ = ["TradingEnv"]
