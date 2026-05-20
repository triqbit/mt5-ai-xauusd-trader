"""Core configuration and settings."""

from typing import TYPE_CHECKING

from src.core.audit_log import AuditLogger, get_audit_logger
from src.core.config import TradingConfig, get_config
from src.core.decision_support import DecisionPacket, DecisionSupportSystem
from src.core.explainability import SignalExplainer, SignalExplanation
from src.core.health import HealthChecker, HealthReport, HealthStatus
from src.core.monitor import Monitor
from src.core.profiler import profile

if TYPE_CHECKING:
    from src.core.feature_engineering import FeatureEngineer
else:
    # Lazy load FeatureEngineer to avoid early talib dependency
    def __getattr__(name):
        if name == "FeatureEngineer":
            from src.core.feature_engineering import FeatureEngineer

            return FeatureEngineer
        if name == "health":
            import src.core.health as health

            return health
        raise AttributeError(f"module {__name__} has no attribute {name}")


__all__ = [
    "AuditLogger",
    "DecisionPacket",
    "DecisionSupportSystem",
    "FeatureEngineer",
    "HealthChecker",
    "HealthReport",
    "HealthStatus",
    "Monitor",
    "SignalExplainer",
    "SignalExplanation",
    "TradingConfig",
    "get_audit_logger",
    "get_config",
    "profile",
]
