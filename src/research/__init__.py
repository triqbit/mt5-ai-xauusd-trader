"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/__init__.py
Research and evaluation modules.
"""

from src.research.benchmarks import (
    BenchmarkEvaluator,
    BenchmarkStrategy,
    EMACrossoverStrategy,
    MeanReversionStrategy,
    MomentumStrategy,
    NaiveDirectionalStrategy,
    RandomStrategy,
    RiskFilteredBaseline,
    VolatilityBreakoutStrategy,
)
from src.research.rare_event_simulator import (
    RareEventConfig,
    RareEventResult,
    RareEventSimulator,
    RareEventType,
)
from src.research.reporting import ResearchReport, ResearchReporter
from src.research.stress_lab import StressLab, StressScenario, StressTestMetrics

__all__ = [
    "BenchmarkEvaluator",
    "BenchmarkStrategy",
    "EMACrossoverStrategy",
    "MeanReversionStrategy",
    "MomentumStrategy",
    "NaiveDirectionalStrategy",
    "RandomStrategy",
    "RareEventConfig",
    "RareEventResult",
    "RareEventSimulator",
    "RareEventType",
    "ResearchReport",
    "ResearchReporter",
    "RiskFilteredBaseline",
    "StressLab",
    "StressScenario",
    "StressTestMetrics",
    "VolatilityBreakoutStrategy",
]
