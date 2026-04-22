"""src/environment package - Gymnasium trading environment."""

from __future__ import annotations

try:
    from .gym_env import TradingEnv
except ImportError:
    TradingEnv = None

__all__ = ["TradingEnv"]
