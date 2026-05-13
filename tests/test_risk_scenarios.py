"""
Unit tests for RiskScenarioBuilder.
"""
import pytest

from src.core.schemas import TradeSignal
from src.utils.synthetic_data import RiskScenarioBuilder


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

def test_daily_loss_breach(risk_builder):
    signals = risk_builder.daily_loss_breach(n_losses=2)
    assert len(signals) == 2
    assert signals[0].lot_size == 1.0
    # Stop loss is 50 pips/points below entry
    assert signals[0].entry_price - signals[0].stop_loss == 50

def test_drawdown_circuit_breaker(risk_builder):
    signals = risk_builder.drawdown_circuit_breaker()
    assert len(signals) == 1
    assert signals[0].lot_size == 2.0
    # Massive stop loss
    assert signals[0].entry_price - signals[0].stop_loss == 500
