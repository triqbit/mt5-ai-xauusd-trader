"""
Tests for ExecutionFilter using synthetic scenarios.
"""
from datetime import UTC, datetime

import pytest

from src.core.config import TradingConfig
from src.trading.execution_filter import ExecutionFilter
from src.utils.synthetic_data import ExecutionScenarioBuilder, ModelHealthGenerator


@pytest.fixture
def execution_builder():
    return ExecutionScenarioBuilder(seed=42)

@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("MT5_PASSWORD", "fake_password")
    monkeypatch.setenv("MT5_SERVER", "fake_server")
    return TradingConfig(
        model_drift_threshold=0.2,
        model_accuracy_floor=0.6,
        model_calibration_threshold=0.3,
        min_confidence=0.6
    )

@pytest.fixture
def filter_svc(config):
    return ExecutionFilter(config=config)

def test_passing_scenario(filter_svc, execution_builder):
    signal, df = execution_builder.passing_buy()
    # Ensure open market time
    signal = signal.model_copy(update={"timestamp": datetime(2024, 5, 22, 12, 0, tzinfo=UTC)})
    decision = filter_svc.validate(signal, df, current_drawdown=0.0)

    assert decision.is_approved is True
    assert decision.blocked_by is None

def test_atr_failure_scenario(filter_svc, execution_builder):
    signal, df = execution_builder.atr_failure()
    decision = filter_svc.validate(signal, df, current_drawdown=0.0)

    assert decision.is_approved is False
    assert decision.blocked_by == "ATR_VOLATILITY"

def test_trend_failure_scenario(filter_svc, execution_builder):
    signal, df = execution_builder.trend_failure()
    decision = filter_svc.validate(signal, df, current_drawdown=0.0)

    assert decision.is_approved is False
    assert decision.blocked_by == "TREND_ANGLE"

def test_ema_sequence_failure_scenario(filter_svc, execution_builder):
    signal, df = execution_builder.ema_out_of_sequence()
    decision = filter_svc.validate(signal, df, current_drawdown=0.0)

    # In a stale regime, EMAs will all be equal, which fails the strict > comparison for BUY
    assert decision.is_approved is False
    assert decision.blocked_by == "EMA_SEQUENCE"

def test_momentum_failure_scenario(filter_svc, execution_builder):
    signal, df = execution_builder.momentum_failure()
    decision = filter_svc.validate(signal, df, current_drawdown=0.0)

    # Rapid trend strength 0.05 will spike RSI > 75
    assert decision.is_approved is False
    assert decision.blocked_by == "MOMENTUM"

def test_model_health_drift_failure(filter_svc, execution_builder):
    signal, df = execution_builder.passing_buy()
    signal = signal.model_copy(update={"timestamp": datetime(2024, 5, 22, 12, 0, tzinfo=UTC)})
    health = ModelHealthGenerator.degraded_drift()
    decision = filter_svc.validate(signal, df, current_drawdown=0.0, model_health=health)

    assert decision.is_approved is False
    assert decision.blocked_by == "MODEL_STABILITY"
    assert decision.trace["model_stability"]["passed"] is False
    assert decision.trace["model_stability"]["drift"] == 0.35

def test_model_health_accuracy_failure(filter_svc, execution_builder):
    signal, df = execution_builder.passing_buy()
    signal = signal.model_copy(update={"timestamp": datetime(2024, 5, 22, 12, 0, tzinfo=UTC)})
    health = ModelHealthGenerator.degraded_accuracy()
    decision = filter_svc.validate(signal, df, current_drawdown=0.0, model_health=health)

    assert decision.is_approved is False
    assert decision.blocked_by == "MODEL_STABILITY"
    assert decision.trace["model_stability"]["accuracy"] == 0.45
