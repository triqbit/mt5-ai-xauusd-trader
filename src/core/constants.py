"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/constants.py
Centralized constants to ensure system-wide consistency.
"""

# Re-export from types for backward compatibility where needed,
# but new code should use src.core.types
from src.core.types import ModelAction, SignalDirection

__all__ = ["ModelAction", "SignalDirection"]
