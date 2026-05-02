"""
Unit tests for the CapitalAllocator system.
"""

import pytest
from src.trading.capital_allocator import (
    CapitalAllocator,
    StrategyConfig,
    AllocationResult,
    RejectionCode,
)


@pytest.fixture
def allocator():
    return CapitalAllocator(
        total_budget=100000.0,
        max_symbol_risk=0.4,
        max_family_risk=0.4,
        max_total_heat=0.7,
        performance_step=0.1,
        decay_rate=0.01,
    )


def test_add_strategy(allocator):
    config = StrategyConfig(
        strategy_id="gold_ppo",
        symbol="XAUUSD",
        model_family="RL",
        capital_cap=50000.0,
    )
    allocator.add_strategy(config)
    assert "gold_ppo" in allocator.strategies
    assert allocator.current_allocations["gold_ppo"] == 0.0


def test_request_allocation_success(allocator):
    config = StrategyConfig(
        strategy_id="gold_ppo",
        symbol="XAUUSD",
        model_family="RL",
        capital_cap=50000.0,
    )
    allocator.add_strategy(config)

    # Request 1% risk
    result = allocator.request_allocation("gold_ppo", 0.01)

    assert result.is_allowed is True
    assert result.allocated_amount == 1000.0
    assert result.allocated_risk_pct == 0.01
    assert result.requested_risk_pct == 0.01


def test_adaptive_allocation(allocator):
    config = StrategyConfig(
        strategy_id="gold_ppo",
        symbol="XAUUSD",
        model_family="RL",
        capital_cap=50000.0,
        performance_multiplier=1.5,
    )
    allocator.add_strategy(config)

    # Request 1% risk, should be scaled to 1.5%
    result = allocator.request_allocation("gold_ppo", 0.01)

    assert result.is_allowed is True
    assert result.allocated_amount == 1500.0
    assert result.allocated_risk_pct == 0.015
    assert result.requested_risk_pct == 0.01


def test_capital_cap(allocator):
    config = StrategyConfig(
        strategy_id="gold_ppo",
        symbol="XAUUSD",
        model_family="RL",
        capital_cap=5000.0,  # Low cap
    )
    allocator.add_strategy(config)

    # Request 10% risk (10000), should be capped at 5000
    result = allocator.request_allocation("gold_ppo", 0.1)

    assert result.is_allowed is True
    assert result.allocated_amount == 5000.0
    assert result.allocated_risk_pct == 0.05
    assert result.requested_risk_pct == 0.1


def test_total_heat_limit(allocator):
    config = StrategyConfig(
        strategy_id="s1",
        symbol="XAUUSD",
        model_family="RL",
        capital_cap=100000.0,
    )
    allocator.add_strategy(config)

    # Commit 65% of budget
    allocator.update_allocation("s1", 65000.0)

    # Request another 10% risk, should be rejected (Total heat limit 0.7)
    result = allocator.request_allocation("s1", 0.1)

    assert result.is_allowed is False
    assert result.rejection_code == RejectionCode.TOTAL_HEAT_LIMIT
    assert "Total heat limit reached" in result.rejection_reason


def test_symbol_concentration_limit(allocator):
    s1_config = StrategyConfig(
        strategy_id="s1",
        symbol="XAUUSD",
        model_family="RL",
        capital_cap=100000.0,
    )
    s2_config = StrategyConfig(
        strategy_id="s2",
        symbol="XAUUSD",
        model_family="LSTM",
        capital_cap=100000.0,
    )
    allocator.add_strategy(s1_config)
    allocator.add_strategy(s2_config)

    # s1 uses 35% of budget on XAUUSD
    allocator.update_allocation("s1", 35000.0)

    # s2 requests 10% on XAUUSD, should be rejected (Symbol limit 0.4)
    result = allocator.request_allocation("s2", 0.1)

    assert result.is_allowed is False
    assert result.rejection_code == RejectionCode.SYMBOL_CONCENTRATION_LIMIT
    assert "Symbol concentration limit reached" in result.rejection_reason


def test_family_concentration_limit(allocator):
    s1_config = StrategyConfig(
        strategy_id="s1",
        symbol="XAUUSD",
        model_family="RL",
        capital_cap=100000.0,
    )
    s2_config = StrategyConfig(
        strategy_id="s2",
        symbol="EURUSD",
        model_family="RL",
        capital_cap=100000.0,
    )
    allocator.add_strategy(s1_config)
    allocator.add_strategy(s2_config)

    # s1 uses 35% of budget on RL family
    allocator.update_allocation("s1", 35000.0)

    # s2 requests 10% on RL family, should be rejected (Family limit 0.4)
    result = allocator.request_allocation("s2", 0.1)

    assert result.is_allowed is False
    assert result.rejection_code == RejectionCode.FAMILY_CONCENTRATION_LIMIT
    assert "Family concentration limit reached" in result.rejection_reason


def test_unregistered_strategy(allocator):
    result = allocator.request_allocation("unknown", 0.01)
    assert result.is_allowed is False
    assert result.rejection_code == RejectionCode.STRATEGY_NOT_FOUND
    assert result.rejection_reason == "Strategy not registered"


def test_update_strategy_performance(allocator):
    config = StrategyConfig(
        strategy_id="s1",
        symbol="XAUUSD",
        model_family="RL",
        capital_cap=50000.0,
    )
    allocator.add_strategy(config)

    # Multiplier starts at 1.0
    assert allocator.strategies["s1"].performance_multiplier == 1.0

    # Positive PnL should increase multiplier
    allocator.update_strategy_performance("s1", 100.0)
    assert allocator.strategies["s1"].performance_multiplier == 1.1
    assert allocator.strategies["s1"].historical_pnl == 100.0

    # Negative PnL should decrease multiplier
    allocator.update_strategy_performance("s1", -50.0)
    assert allocator.strategies["s1"].performance_multiplier == 1.0
    assert allocator.strategies["s1"].historical_pnl == 50.0

    # Multiplier should cap at 2.0
    for _ in range(20):
        allocator.update_strategy_performance("s1", 10.0)
    assert allocator.strategies["s1"].performance_multiplier == 2.0

    # Multiplier should floor at 0.0
    for _ in range(30):
        allocator.update_strategy_performance("s1", -10.0)
    assert allocator.strategies["s1"].performance_multiplier == 0.0


def test_decay_performance_multipliers(allocator):
    config_high = StrategyConfig(
        strategy_id="high",
        symbol="XAUUSD",
        model_family="RL",
        capital_cap=50000.0,
        performance_multiplier=1.5,
    )
    config_low = StrategyConfig(
        strategy_id="low",
        symbol="EURUSD",
        model_family="LSTM",
        capital_cap=50000.0,
        performance_multiplier=0.5,
    )
    allocator.add_strategy(config_high)
    allocator.add_strategy(config_low)

    allocator.decay_performance_multipliers()
    assert allocator.strategies["high"].performance_multiplier == 1.49
    assert allocator.strategies["low"].performance_multiplier == 0.51

    # Should not decay past 1.0
    allocator.strategies["high"].performance_multiplier = 1.005
    allocator.decay_performance_multipliers()
    assert allocator.strategies["high"].performance_multiplier == 1.0


def test_get_strategy_utilization(allocator):
    config = StrategyConfig(
        strategy_id="s1",
        symbol="XAUUSD",
        model_family="RL",
        capital_cap=10000.0,
    )
    allocator.add_strategy(config)

    assert allocator.get_strategy_utilization("s1") == 0.0

    allocator.update_allocation("s1", 5000.0)
    assert allocator.get_strategy_utilization("s1") == 0.5

    allocator.update_allocation("s1", 10000.0)
    assert allocator.get_strategy_utilization("s1") == 1.0


def test_request_allocation_zero_cap(allocator):
    # This shouldn't happen with Pydantic validation (gt=0), but let's test logic if cap was 0
    # Actually Pydantic will raise error on StrategyConfig creation.
    with pytest.raises(Exception):
        StrategyConfig(
            strategy_id="s1",
            symbol="XAUUSD",
            model_family="RL",
            capital_cap=0.0,
        )


def test_complex_scaling_and_capping(allocator):
    # Test that performance multiplier is applied, then capped, and then safety checked.
    config = StrategyConfig(
        strategy_id="s1",
        symbol="XAUUSD",
        model_family="RL",
        capital_cap=20000.0,  # 20% cap
        performance_multiplier=2.0,
    )
    allocator.add_strategy(config)

    # Request 15% risk. Multiplier 2.0 makes it 30%.
    # 30% is 30000, which is capped to 20000 (20%).
    # So allocated_risk_pct should be 0.2

    result = allocator.request_allocation("s1", 0.15)

    assert result.is_allowed is True
    assert result.allocated_amount == 20000.0
    assert result.allocated_risk_pct == 0.2
    assert result.requested_risk_pct == 0.15

    # Now verify safety check uses the capped 20%
    # If we set symbol limit to 25%, and s1 already uses 10%...
    allocator.max_symbol_risk = 0.25

    other_config = StrategyConfig(
        strategy_id="other", symbol="XAUUSD", model_family="Other", capital_cap=100000.0
    )
    allocator.add_strategy(other_config)
    allocator.update_allocation("other", 10000.0)  # other uses 10%

    # s1 requests 15% -> scaled to 30% -> capped to 20%.
    # Total symbol risk = 10% (other) + 20% (s1) = 30%.
    # 30% > 25% (limit) -> should be rejected.

    result = allocator.request_allocation("s1", 0.15)
    assert result.is_allowed is False
    assert result.rejection_code == RejectionCode.SYMBOL_CONCENTRATION_LIMIT
