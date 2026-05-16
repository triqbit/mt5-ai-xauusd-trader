"""
Unit tests for the new features of the CapitalAllocator system.
"""

import pytest
from src.trading.capital_allocator import (
    CapitalAllocator,
    StrategyConfig,
    RejectionCode,
)

@pytest.fixture
def allocator():
    return CapitalAllocator(
        total_budget=100000.0,
        max_symbol_risk=0.4,
        max_family_risk=0.4,
        max_total_heat=0.7,
        max_strategy_risk=0.2,
        performance_step=0.1,
        decay_rate=0.01,
        soft_limit_buffer=0.0,  # Disable soft buffer for easier hard limit testing
    )

def test_strategy_concentration_limit(allocator):
    """Test that the strategy-level concentration limit is enforced."""
    config = StrategyConfig(
        strategy_id="s1",
        symbol="XAUUSD",
        model_family="RL",
        capital_cap=100000.0,
        max_allocation_pct=0.15, # 15% limit
    )
    allocator.add_strategy(config)

    # Request 10% risk -> should be allowed
    res1 = allocator.request_allocation("s1", 0.1)
    assert res1.is_allowed is True
    allocator.update_allocation("s1", res1.allocated_amount)

    # Request another 10% risk -> total would be 20% > 15% limit -> should be rejected
    res2 = allocator.request_allocation("s1", 0.1)
    assert res2.is_allowed is False
    assert res2.rejection_code == RejectionCode.STRATEGY_CONCENTRATION_LIMIT

def test_global_strategy_risk_limit(allocator):
    """Test that the global max_strategy_risk limit is enforced."""
    allocator.max_strategy_risk = 0.1 # 10% global limit
    config = StrategyConfig(
        strategy_id="s1",
        symbol="XAUUSD",
        model_family="RL",
        capital_cap=100000.0,
        max_allocation_pct=0.2, # 20% strategy-specific limit
    )
    allocator.add_strategy(config)

    # Request 15% risk -> should be rejected by global 10% limit
    res = allocator.request_allocation("s1", 0.15)
    assert res.is_allowed is False
    assert res.rejection_code == RejectionCode.STRATEGY_CONCENTRATION_LIMIT

def test_route_allocation_with_performance_tie_break(allocator):
    """Test that route_allocation breaks ties using performance multiplier."""
    s1 = StrategyConfig(
        strategy_id="s1",
        symbol="XAUUSD",
        model_family="RL",
        capital_cap=50000.0,
        performance_multiplier=1.0
    )
    s2 = StrategyConfig(
        strategy_id="s2",
        symbol="XAUUSD",
        model_family="RL",
        capital_cap=50000.0,
        performance_multiplier=1.5 # Better multiplier
    )
    allocator.add_strategy(s1)
    allocator.add_strategy(s2)

    # Both strategies are identical in terms of diversification impact for a first trade
    # But s2 has a higher multiplier.
    result = allocator.route_allocation("XAUUSD", 0.01)
    assert result.strategy_id == "s2"

def test_get_active_allocations(allocator):
    """Test that get_active_allocations returns only strategies with > 0 allocation."""
    s1 = StrategyConfig(strategy_id="s1", symbol="XAUUSD", model_family="RL", capital_cap=50000.0)
    s2 = StrategyConfig(strategy_id="s2", symbol="EURUSD", model_family="RL", capital_cap=50000.0)
    allocator.add_strategy(s1)
    allocator.add_strategy(s2)

    allocator.update_allocation("s1", 1000.0)

    active = allocator.get_active_allocations()
    assert "s1" in active
    assert active["s1"] == 1000.0
    assert "s2" not in active
    assert len(active) == 1
