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
from src.research.hyperopt_walkforward import (
    WalkForwardConfig,
    WalkForwardOptimizer,
    WalkForwardResult,
)
from src.research.rare_event_simulator import (
    RareEventConfig,
    RareEventResult,
    RareEventSimulator,
    RareEventType,
)
from src.research.reporting import ResearchReport, ResearchReporter
from src.research.rl_evaluation import (
    MeanReversionBaseline,
    MomentumBaseline,
    RandomBaseline,
    RLEvaluator,
    RLReport,
)
from src.research.stress_lab import StressLab, StressScenario, StressTestMetrics

__all__ = [
    "BenchmarkEvaluator",
    "BenchmarkStrategy",
    "EMACrossoverStrategy",
    "MeanReversionBaseline",
    "MeanReversionStrategy",
    "MomentumBaseline",
    "MomentumStrategy",
    "NaiveDirectionalStrategy",
    "RLEvaluator",
    "RLReport",
    "RandomBaseline",
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
    "WalkForwardConfig",
    "WalkForwardOptimizer",
    "WalkForwardResult",
]
