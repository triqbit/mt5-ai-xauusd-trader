"""Core configuration and settings."""

from typing import TYPE_CHECKING

from src.core.audit_log import AuditLogger, get_audit_logger
from src.core.config import TradingConfig, get_config
from src.core.decision_support import DecisionPacket, DecisionSupportSystem
from src.core.explainability import SignalExplainer, SignalExplanation
from src.core.monitor import Monitor
from src.core.profiler import profile

# FeatureEngineer moved to src.data.feature_engineering

__all__ = [
    "AuditLogger",
    "DecisionPacket",
    "DecisionSupportSystem",
    "Monitor",
    "SignalExplainer",
    "SignalExplanation",
    "TradingConfig",
    "get_audit_logger",
    "get_config",
    "profile",
]
