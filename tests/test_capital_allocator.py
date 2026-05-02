"""
Unit tests for the CapitalAllocator system.
"""

import pytest
from src.trading.capital_allocator import CapitalAllocator, StrategyConfig, AllocationResult


@pytest.fixture
def allocator():
    return CapitalAllocator(
        total_budget=100000.0,
        max_symbol_risk=0.4,
        max_family_risk=0.4,
        max_total_heat=0.7,
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
    assert result.risk_pct == 0.01


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
    assert result.risk_pct == 0.015


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
    assert result.risk_pct == 0.05


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
    assert "Family concentration limit reached" in result.rejection_reason


def test_unregistered_strategy(allocator):
    result = allocator.request_allocation("unknown", 0.01)
    assert result.is_allowed is False
    assert result.rejection_reason == "Strategy not registered"
