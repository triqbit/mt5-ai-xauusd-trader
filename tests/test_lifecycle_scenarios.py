"""
Tests for operational lifecycle and execution quality scenarios.
"""
import os

import pytest

from src.core.trade_logger import TradeLogger
from src.models.regime_detector import MarketRegime, RegimeDetector
from src.utils.synthetic_data import (
    ExecutionQualityScenarioBuilder,
    LifecycleScenarioBuilder,
    ScenarioGenerator,
)


@pytest.fixture
def scenario_gen():
    return ScenarioGenerator(seed=42)

@pytest.fixture
def lifecycle_builder():
    return LifecycleScenarioBuilder(seed=42)

@pytest.fixture
def exec_quality_builder():
    return ExecutionQualityScenarioBuilder(seed=42)

def test_scenario_generator_spread(scenario_gen):
    """Verify that the generator now produces spread data."""
    df = scenario_gen.generate(n_steps=100, regime="ranging")
    assert "spread_pips" in df.columns
    assert (df["spread_pips"] >= 0.8).all()
    assert (df["spread_pips"] <= 1.3).all()

def test_high_spread_injection(scenario_gen):
    """Verify that spread faults can be injected."""
    df = scenario_gen.generate(n_steps=100, regime="ranging")
    df_faulty = scenario_gen.inject_faults(df, fault_type="high_spread", prob=0.2)

    # Some spreads should now be significantly higher (e.g., > 4.0 pips)
    assert (df_faulty["spread_pips"] > 4.0).any()

def test_flash_crash_recovery_cycle(lifecycle_builder):
    """Verify the multi-stage flash crash recovery sequence."""
    df, _events = lifecycle_builder.flash_crash_recovery_cycle(n_steps=300)
    assert len(df) == 300

    # Use RegimeDetector to verify the stages
    detector = RegimeDetector(window=20)

    # 1. First 100 bars: Stable
    info_start = detector.detect(df.iloc[:100])
    assert info_start.label in [MarketRegime.RANGING, MarketRegime.LOW_VOLATILITY_DRIFT]

    # 2. Middle 100 bars: Contains Flash Crash
    # Flash crash is at 100-200. Let's check around 150.
    info_crash = detector.detect(df.iloc[:160])
    # The detector label logic is complex, but transition_score should be very high
    assert info_crash.transition_score > 0.5

    # 3. Last 100 bars: Recovery (Trending)
    info_end = detector.detect(df.iloc[200:])
    assert info_end.label == MarketRegime.TRENDING

def test_news_block_lifecycle(lifecycle_builder):
    """Verify news lifecycle produces expected macro events and price shocks."""
    df, events, event_time = lifecycle_builder.news_block_lifecycle(n_steps=200)
    assert len(events) == 1
    assert events[0].name == "Non-Farm Payrolls"

    # Check that the event time aligns with the middle of the dataframe
    # freq is 5min, n_steps=200, mid=100
    assert df.index[100] == event_time

    # Verify price shock at the end (as per news_shock regime)
    last_return = abs(df["close"].iloc[-1] / df["close"].iloc[-2] - 1)
    assert last_return > 0.05 # Massive 10% spike in news_shock

def test_toxic_flow_execution_quality(exec_quality_builder):
    """Verify that toxic flow produces bad win rates and high slippage."""
    trades = exec_quality_builder.toxic_flow_sequence(n_trades=100)

    wins = [t for t in trades if t["pnl"] > 0]
    win_rate = len(wins) / len(trades)
    avg_slippage = sum(t["slippage_pips"] for t in trades) / len(trades)

    assert win_rate < 0.3
    assert avg_slippage > 2.0

def test_performance_guard_with_synthetic_trades(exec_quality_builder):
    """Verify that Performance Guard would trigger on toxic synthetic trades."""
    db_path = "test_perf_lifecycle.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    try:
        logger = TradeLogger(db_url=f"sqlite:///{db_path}")

        # Generate and log 25 toxic trades
        toxic_trades = exec_quality_builder.toxic_flow_sequence(n_trades=25)
        for t in toxic_trades:
            ticket = t["ticket"]
            logger.log_trade(
                ticket=ticket,
                symbol=t["symbol"],
                direction=t["direction"],
                entry_price=2300.0,
                lot_size=0.1
            )
            # Use provided pnl
            logger.update_trade(ticket=ticket, exit_price=2310.0, pnl=t["pnl"])

        report = logger.read_performance_report()
        assert report["total_trades"] == 25
        assert report["win_rate"] < 0.45 # Performance floor is 0.45

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
