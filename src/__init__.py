"""MT5 AI/ML Trading Bot package."""

__version__ = "1.0.0"
__author__ = "triqbit"
__license__ = "MIT"

# Lazy sub-package discovery to avoid early dependency loads during migrations/quality checks
__all__: list[str] = [
    "analytics",
    "core",
    "data",
    "environment",
    "models",
    "monitoring",
    "research",
    "trading",
    "utils",
]
