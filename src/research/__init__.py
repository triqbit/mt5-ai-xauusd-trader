"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/__init__.py
Research and evaluation modules.
"""

from src.research.benchmarks import BenchmarkEvaluator, BenchmarkStrategy
from src.research.reporting import ResearchReport, ResearchReporter
from src.research.stress_lab import StressLab

__all__ = [
    "BenchmarkEvaluator",
    "BenchmarkStrategy",
    "ResearchReport",
    "ResearchReporter",
    "StressLab",
]
