"""
Unit tests for RiskScenarioBuilder.
"""
import pytest
from src.utils.synthetic_data import RiskScenarioBuilder
from src.trading.risk_manager import TradeSignal

@pytest.fixture
def risk_builder():
    return RiskScenarioBuilder(seed=42)

def test_consecutive_losses(risk_builder):
    signals = risk_builder.consecutive_losses(n_signals=3)
    assert len(signals) == 3
    assert all(isinstance(s, TradeSignal) for s in signals)
    assert signals[0].entry_price > signals[1].entry_price
    assert signals[0].direction == 1

def test_ensemble_dissent(risk_builder):
    signals = risk_builder.ensemble_dissent()
    assert len(signals) == 2
    # Check conflicting directions
    assert signals[0].direction == 1
    assert signals[1].direction == -1
    assert signals[0].algorithm == "ppo"
    assert signals[1].algorithm == "lstm"
