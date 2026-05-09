"""MT5 AI/ML Trading Bot package."""

from . import (
    analytics,
    core,
    data,
    environment,
    models,
    monitoring,
    research,
    trading,
    utils,
)

__version__ = "1.1.0-rc7"
__author__ = "triqbit"
__license__ = "MIT"

# Sub-package discovery for enterprise modularity
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
