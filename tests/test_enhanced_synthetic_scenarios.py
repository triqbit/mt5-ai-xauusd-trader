"""
Tests for enhanced synthetic scenarios and builders.
"""

import pytest

from src.core.config import TradingConfig
from src.models.regime_detector import MarketRegime, RegimeDetector
from src.trading.execution_filter import ExecutionFilter
from src.utils.synthetic_data import (
    ExecutionScenarioBuilder,
    RegimeScenarioBuilder,
    ScenarioGenerator,
)


@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("MT5_PASSWORD", "fake_password")
    monkeypatch.setenv("MT5_SERVER", "fake_server")
    return TradingConfig(
        model_drift_threshold=0.2,
        model_accuracy_floor=0.6,
        min_confidence=0.6,
        max_signal_changes=3,
        signal_flicker_window=6
    )

@pytest.fixture
def filter_svc(config):
    return ExecutionFilter(config=config)

@pytest.fixture
def regime_detector():
    return RegimeDetector(window=20, long_window=100)

@pytest.fixture
def execution_builder():
    return ExecutionScenarioBuilder(seed=42)

@pytest.fixture
def regime_builder():
    return RegimeScenarioBuilder(seed=42)

def test_session_violation(filter_svc, execution_builder):
    signal, df, sat = execution_builder.session_violation()
    decision = filter_svc.validate(signal, df, current_drawdown=0.0)

    assert decision.is_approved is False
    assert decision.blocked_by == "SESSION_CLOSED"
    assert sat.weekday() == 5  # Saturday

def test_drawdown_violation(filter_svc, execution_builder):
    signal, df, dd = execution_builder.drawdown_violation()
    decision = filter_svc.validate(signal, df, current_drawdown=dd)

    assert decision.is_approved is False
    assert decision.blocked_by == "DRAWDOWN_LIMIT"

def test_confidence_violation(filter_svc, execution_builder):
    signal, df = execution_builder.confidence_violation()
    decision = filter_svc.validate(signal, df, current_drawdown=0.0)

    assert decision.is_approved is False
    assert decision.blocked_by == "CONFIDENCE_THRESHOLD"
    assert signal.confidence < 0.6

def test_signal_flicker_violation(filter_svc, execution_builder):
    signals = execution_builder.signal_flicker_violation()
    # Use ranging data
    df = ScenarioGenerator().generate(n_steps=300, regime="ranging", volatility=0.0001)

    # Process 10 oscillating signals
    for sig in signals:
        filter_svc.validate(sig, df, current_drawdown=0.0)

    # The last decision should be blocked by flicker guard (signal_consistency)
    # We check the trace specifically since other filters might fail on oscillating signals
    final_sig = signals[-1]
    decision = filter_svc.validate(final_sig, df, current_drawdown=0.0)
    assert decision.trace["signal_consistency"]["passed"] is False

def test_performance_violation(filter_svc, execution_builder):
    signal, df, mock_logger = execution_builder.performance_violation()
    decision = filter_svc.validate(signal, df, current_drawdown=0.0, trade_logger=mock_logger)

    assert decision.is_approved is False
    assert decision.blocked_by == "PERFORMANCE_FLOOR"

def test_regime_trending(regime_detector, regime_builder):
    df = regime_builder.trending()
    info = regime_detector.detect(df)
    assert info.label == MarketRegime.TRENDING

def test_regime_ranging(regime_detector, regime_builder):
    df = regime_builder.ranging()
    info = regime_detector.detect(df)
    assert info.label == MarketRegime.RANGING

def test_regime_mean_reversion(regime_detector, regime_builder):
    df = regime_builder.mean_reversion()
    info = regime_detector.detect(df)
    assert info.label == MarketRegime.MEAN_REVERSION

def test_regime_volatile_breakout(regime_detector, regime_builder):
    df = regime_builder.volatile_breakout()
    info = regime_detector.detect(df)
    assert info.label == MarketRegime.VOLATILE_BREAKOUT

def test_regime_low_volatility_drift(regime_detector, regime_builder):
    df = regime_builder.low_volatility_drift()
    info = regime_detector.detect(df)
    assert info.label == MarketRegime.LOW_VOLATILITY_DRIFT

def test_regime_news_shock(regime_detector, regime_builder):
    df = regime_builder.news_shock()
    info = regime_detector.detect(df)
    assert info.label == MarketRegime.NEWS_SHOCK
