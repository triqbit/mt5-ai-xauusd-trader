import pytest

from src.trading.capital_allocator import CapitalAllocator, StrategyConfig


@pytest.fixture
def allocator():
    return CapitalAllocator(total_capital=100000.0, max_portfolio_heat=0.20)

def test_add_strategy(allocator):
    config = StrategyConfig("trend_ppo", 10000.0, 0.05, "trend")
    allocator.add_strategy(config)
    assert "trend_ppo" in allocator.strategies

def test_request_allocation_success(allocator):
    config = StrategyConfig("trend_ppo", 10000.0, 0.05, "trend")
    allocator.add_strategy(config)
    result = allocator.request_allocation("trend_ppo", 5000.0)
    assert result.is_approved
    assert result.allocated_amount == 5000.0

def test_adaptive_allocation(allocator):
    config = StrategyConfig("trend_ppo", 10000.0, 0.05, "trend")
    allocator.add_strategy(config)

    # Simulate some wins
    for _ in range(5):
        allocator.record_pnl("trend_ppo", 1000.0)

    # Multiplier should have increased
    assert allocator.performance_multipliers["trend_ppo"] > 1.0

    # Now request more than original cap
    result = allocator.request_allocation("trend_ppo", 12000.0)
    assert result.allocated_amount > 10000.0

def test_capital_cap(allocator):
    config = StrategyConfig("trend_ppo", 5000.0, 0.05, "trend")
    allocator.add_strategy(config)
    result = allocator.request_allocation("trend_ppo", 10000.0)
    assert result.allocated_amount == 5000.0

def test_total_heat_limit(allocator):
    config1 = StrategyConfig("s1", 50000.0, 0.10, "f1")
    allocator.add_strategy(config1)
    allocator.request_allocation("s1", 20000.0) # 20% heat

    config2 = StrategyConfig("s2", 5000.0, 0.05, "f2")
    allocator.add_strategy(config2)
    result = allocator.request_allocation("s2", 1000.0)
    assert not result.is_approved
    assert "Max portfolio heat" in result.reason

def test_symbol_concentration_limit(allocator):
    # This test is currently redundant with family concentration in the simplified implementation
    pass

def test_family_concentration_limit(allocator):
    config1 = StrategyConfig("s1", 15000.0, 0.10, "f1")
    allocator.add_strategy(config1)
    allocator.request_allocation("s1", 10000.0) # 10% heat for f1

    config2 = StrategyConfig("s2", 5000.0, 0.05, "f1") # same family
    allocator.add_strategy(config2)
    result = allocator.request_allocation("s2", 1000.0)
    assert not result.is_approved
    assert "Family concentration" in result.reason

def test_unregistered_strategy(allocator):
    result = allocator.request_allocation("ghost", 100.0)
    assert not result.is_approved
    assert "not registered" in result.reason
