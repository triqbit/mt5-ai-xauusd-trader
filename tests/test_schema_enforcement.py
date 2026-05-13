import pytest
from pydantic import ValidationError

from src.core.constants import SignalDirection
from src.core.decision_support import PerformanceContext
from src.core.explainability import (
    FeatureContribution,
    ModelAttribution,
)
from src.models.regime_detector import MarketRegime, RegimeInfo


def test_explainability_extra_forbid():
    with pytest.raises(ValidationError):
        FeatureContribution(
            cluster_name="Trend",
            contribution_score=0.5,
            impact_level="High",
            summary="Test",
            extra_field="invalid"
        )

def test_explainability_frozen():
    fc = FeatureContribution(
        cluster_name="Trend",
        contribution_score=0.5,
        impact_level="High",
        summary="Test"
    )
    with pytest.raises(ValidationError):
        fc.contribution_score = 0.8

def test_explainability_range_constraints():
    with pytest.raises(ValidationError):
        FeatureContribution(
            cluster_name="Trend",
            contribution_score=1.5,  # Should be <= 1.0
            impact_level="High",
            summary="Test"
        )
    with pytest.raises(ValidationError):
        ModelAttribution(
            model_name="PPO",
            vote=SignalDirection.BUY,
            confidence=1.1,  # Should be <= 1.0
            weight=0.5
        )

def test_performance_context_constraints():
    with pytest.raises(ValidationError):
        PerformanceContext(sharpe_ratio=11.0)  # Should be <= 10.0
    with pytest.raises(ValidationError):
        PerformanceContext(max_drawdown=1.5)   # Should be <= 1.0
    with pytest.raises(ValidationError):
        PerformanceContext(profit_factor=-1.0) # Should be >= 0.0

def test_regime_info_constraints():
    with pytest.raises(ValidationError):
        RegimeInfo(
            label=MarketRegime.TRENDING,
            confidence=1.2,  # Should be <= 1.0
            transition_score=0.5,
            volatility_index=1.0
        )
    with pytest.raises(ValidationError):
        RegimeInfo(
            label=MarketRegime.TRENDING,
            confidence=0.8,
            transition_score=-0.1,  # Should be >= 0.0
            volatility_index=1.0
        )
    with pytest.raises(ValidationError):
        RegimeInfo(
            label=MarketRegime.TRENDING,
            confidence=0.8,
            transition_score=0.5,
            volatility_index=1.0,
            extra="forbidden"
        )
