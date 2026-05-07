"""
Tests for ExecutionFilter using synthetic scenarios.
"""
import pytest
from datetime import datetime, UTC

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
        min_confidence=0.6,
        signal_flicker_window=6,
        max_signal_changes=3
    )

@pytest.fixture
def filter_svc(config):
    return ExecutionFilter(config=config)

def test_passing_scenario(filter_svc, execution_builder):
    scenario = execution_builder.passing_buy()
    decision = filter_svc.validate(
        scenario.signal,
        scenario.market_data,
        current_drawdown=scenario.current_drawdown
    )

    assert decision.is_approved is True
    assert decision.blocked_by is None

def test_atr_failure_scenario(filter_svc, execution_builder):
    scenario = execution_builder.atr_failure()
    decision = filter_svc.validate(
        scenario.signal,
        scenario.market_data,
        current_drawdown=scenario.current_drawdown
    )

    assert decision.is_approved is False
    assert decision.blocked_by == "ATR_VOLATILITY"

def test_trend_failure_scenario(filter_svc, execution_builder):
    scenario = execution_builder.trend_failure()
    decision = filter_svc.validate(
        scenario.signal,
        scenario.market_data,
        current_drawdown=scenario.current_drawdown
    )

    assert decision.is_approved is False
    assert decision.blocked_by == "TREND_ANGLE"

def test_ema_sequence_failure_scenario(filter_svc, execution_builder):
    scenario = execution_builder.ema_out_of_sequence()
    decision = filter_svc.validate(
        scenario.signal,
        scenario.market_data,
        current_drawdown=scenario.current_drawdown
    )

    assert decision.is_approved is False
    assert decision.blocked_by == "EMA_SEQUENCE"

def test_momentum_failure_scenario(filter_svc, execution_builder):
    scenario = execution_builder.momentum_failure()
    decision = filter_svc.validate(
        scenario.signal,
        scenario.market_data,
        current_drawdown=scenario.current_drawdown
    )

    assert decision.is_approved is False
    assert decision.blocked_by == "MOMENTUM"

def test_model_health_drift_failure(filter_svc, execution_builder):
    scenario = execution_builder.passing_buy()
    health = ModelHealthGenerator.degraded_drift()
    decision = filter_svc.validate(
        scenario.signal,
        scenario.market_data,
        current_drawdown=scenario.current_drawdown,
        model_health=health
    )

    assert decision.is_approved is False
    assert decision.blocked_by == "MODEL_STABILITY"
    assert decision.trace["model_stability"]["passed"] is False
    assert decision.trace["model_stability"]["drift"] == 0.35

def test_model_health_accuracy_failure(filter_svc, execution_builder):
    scenario = execution_builder.passing_buy()
    health = ModelHealthGenerator.degraded_accuracy()
    decision = filter_svc.validate(
        scenario.signal,
        scenario.market_data,
        current_drawdown=scenario.current_drawdown,
        model_health=health
    )

    assert decision.is_approved is False
    assert decision.blocked_by == "MODEL_STABILITY"
    assert decision.trace["model_stability"]["accuracy"] == 0.45

def test_session_violation(filter_svc, execution_builder):
    scenario = execution_builder.session_violation()
    decision = filter_svc.validate(
        scenario.signal,
        scenario.market_data,
        current_drawdown=scenario.current_drawdown,
        timestamp=scenario.timestamp
    )
    assert decision.is_approved is False
    assert decision.blocked_by == "SESSION_TIME"

def test_drawdown_breach(filter_svc, execution_builder):
    scenario = execution_builder.drawdown_breach()
    decision = filter_svc.validate(
        scenario.signal,
        scenario.market_data,
        current_drawdown=scenario.current_drawdown
    )
    assert decision.is_approved is False
    assert decision.blocked_by == "DRAWDOWN_LIMIT"

def test_confidence_failure(filter_svc, execution_builder):
    scenario = execution_builder.confidence_failure()
    decision = filter_svc.validate(
        scenario.signal,
        scenario.market_data,
        current_drawdown=scenario.current_drawdown
    )
    assert decision.is_approved is False
    assert decision.blocked_by == "CONFIDENCE_THRESHOLD"

def test_performance_floor_failure(filter_svc, execution_builder):
    scenario = execution_builder.performance_floor_failure()
    decision = filter_svc.validate(
        scenario.signal,
        scenario.market_data,
        current_drawdown=scenario.current_drawdown,
        trade_logger=scenario.trade_logger
    )
    assert decision.is_approved is False
    assert decision.blocked_by == "PERFORMANCE_FLOOR"

def test_flicker_guard_failure(filter_svc, execution_builder):
    scenarios = execution_builder.flicker_sequence()
    decisions = []
    for i, s in enumerate(scenarios):
        # We use precomputed metrics to force layers 1-4 to pass
        # so we can test Layer 10 (consistency) in isolation.
        direction = s.signal.direction
        precomputed = {
            "atr_volatility": {"current_atr": 1.0, "avg_atr": 1.0}, # ratio 1.0 <= 3.0
            "trend_angle": {"slope": 1.0 if direction > 0 else -1.0}, # matching slope
            "ema_sequence": {
                "emas": {
                    8: 104 if direction > 0 else 96,
                    21: 103 if direction > 0 else 97,
                    50: 102 if direction > 0 else 98,
                    200: 101 if direction > 0 else 99
                }
            },
            "momentum": {"rsi": 60 if direction > 0 else 40} # in range
        }

        decisions.append(filter_svc.validate(
            s.signal,
            s.market_data,
            current_drawdown=s.current_drawdown,
            precomputed_metrics=precomputed
        ))

    # The first few should pass (depending on threshold)
    # flicker_sequence generates 5 signals alternating.
    # Window is 6, max_changes is 3.
    # 1: BUY (0 changes) - OK
    # 2: SELL (1 change) - OK
    # 3: BUY (2 changes) - OK
    # 4: SELL (3 changes) - OK
    # 5: BUY (4 changes) - BLOCKED

    assert decisions[0].is_approved is True
    assert decisions[3].is_approved is True
    assert decisions[4].is_approved is False
    assert decisions[4].blocked_by == "SIGNAL_CONSISTENCY"

def test_missing_data_resilience(filter_svc, execution_builder):
    """Verify ExecutionFilter handles data holes without crashing."""
    scenario = execution_builder.passing_buy()
    # Inject holes into market data
    scenario.market_data = execution_builder.gen.generate_with_holes(n_steps=300, hole_pct=0.3)

    # This should not raise an exception
    decision = filter_svc.validate(
        scenario.signal,
        scenario.market_data,
        current_drawdown=scenario.current_drawdown
    )
    # It might pass or fail depending on where the holes are, but it shouldn't crash.
    assert isinstance(decision.is_approved, bool)

def test_stale_data_handling(filter_svc, execution_builder):
    """Verify ExecutionFilter handles stale (frozen) data."""
    scenario = execution_builder.passing_buy()
    # Inject stale bars
    scenario.market_data = execution_builder.gen.generate_stale_feed(n_steps=300, stale_len=10)

    decision = filter_svc.validate(
        scenario.signal,
        scenario.market_data,
        current_drawdown=scenario.current_drawdown
    )
    assert isinstance(decision.is_approved, bool)
