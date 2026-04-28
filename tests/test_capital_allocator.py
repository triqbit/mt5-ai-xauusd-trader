import pytest
from src.trading.capital_allocator import (
    CapitalAllocator,
    StrategyConfig,
    AllocationRequest
)

@pytest.fixture
def allocator():
    strategies = [
        StrategyConfig(strategy_id="ppo_trend", capital_cap=0.3, base_allocation=0.1),
        StrategyConfig(strategy_id="lstm_reversion", capital_cap=0.2, base_allocation=0.05)
    ]
    return CapitalAllocator(strategies=strategies, max_portfolio_heat=0.4)

def test_initialization(allocator):
    assert len(allocator.strategies) == 2
    assert allocator.max_portfolio_heat == 0.4
    assert allocator._calculate_portfolio_heat() == 0.0

def test_successful_allocation(allocator):
    request = AllocationRequest(
        strategy_id="ppo_trend",
        symbol="XAUUSD",
        current_balance=10000.0,
        confidence=1.0
    )
    result = allocator.get_allocation(request)

    assert result.approved is True
    assert result.allocation_fraction == 0.1
    assert result.allocated_amount == 1000.0
    assert result.portfolio_heat == 0.1

def test_portfolio_heat_limit(allocator):
    # Fill up the heat
    req1 = AllocationRequest(strategy_id="ppo_trend", symbol="XAUUSD", current_balance=10000.0)
    allocator.get_allocation(req1) # 0.1

    req2 = AllocationRequest(strategy_id="ppo_trend", symbol="GBPUSD", current_balance=10000.0)
    allocator.get_allocation(req2) # +0.1 = 0.2

    req3 = AllocationRequest(strategy_id="ppo_trend", symbol="EURUSD", current_balance=10000.0)
    allocator.get_allocation(req3) # +0.1 = 0.3

    # Next one should still fit (max 0.4)
    req4 = AllocationRequest(strategy_id="lstm_reversion", symbol="USDJPY", current_balance=10000.0)
    res4 = allocator.get_allocation(req4) # +0.05 = 0.35
    assert res4.approved is True

    # Next one should be capped or rejected
    req5 = AllocationRequest(strategy_id="lstm_reversion", symbol="AUDUSD", current_balance=10000.0)
    res5 = allocator.get_allocation(req5)

    # Remaining heat is 0.05. lstm_reversion base is 0.05.
    # Should approve 0.05 and hit exactly 0.4 heat.
    assert res5.approved is True
    assert allocator._calculate_portfolio_heat() == 0.4

    # Now it should reject
    req6 = AllocationRequest(strategy_id="ppo_trend", symbol="NZDUSD", current_balance=10000.0)
    res6 = allocator.get_allocation(req6)
    assert res6.approved is False
    assert "Max portfolio heat reached" in res6.reason

def test_strategy_cap(allocator):
    # ppo_trend cap is 0.3, base is 0.1
    # Use different symbols to avoid symbol concentration limits
    allocator.get_allocation(AllocationRequest(strategy_id="ppo_trend", symbol="S1", current_balance=10000.0))
    allocator.get_allocation(AllocationRequest(strategy_id="ppo_trend", symbol="S2", current_balance=10000.0))
    allocator.get_allocation(AllocationRequest(strategy_id="ppo_trend", symbol="S3", current_balance=10000.0)) # Total 0.3

    req2 = AllocationRequest(strategy_id="ppo_trend", symbol="S4", current_balance=10000.0)
    res2 = allocator.get_allocation(req2)

    assert res2.approved is False
    assert "Allocation below minimum threshold" in res2.reason

def test_symbol_concentration(allocator):
    # Max heat 0.4. Symbol cap is 50% of max heat = 0.2.
    req = AllocationRequest(strategy_id="ppo_trend", symbol="XAUUSD", current_balance=10000.0)
    allocator.get_allocation(req) # 0.1
    allocator.get_allocation(req) # 0.1 (total 0.2 for XAUUSD)

    # Third one for XAUUSD should be rejected/capped
    res = allocator.get_allocation(req)
    assert res.approved is False

def test_adaptive_budgeting(allocator):
    # Strategy 'ppo_trend' starts at 0.1 base
    # Give it some losses
    for _ in range(10):
        allocator.update_performance("ppo_trend", -100.0)

    req = AllocationRequest(strategy_id="ppo_trend", symbol="XAUUSD", current_balance=10000.0)
    res = allocator.get_allocation(req)

    # Win rate 0% < 40%, multiplier should be 0.8
    # 0.1 * 0.8 = 0.08
    assert res.allocation_fraction == pytest.approx(0.08)

def test_release_allocation(allocator):
    req = AllocationRequest(strategy_id="ppo_trend", symbol="XAUUSD", current_balance=10000.0)
    res = allocator.get_allocation(req)
    assert allocator._calculate_portfolio_heat() == 0.1

    allocator.release_allocation("ppo_trend", "XAUUSD", res.allocation_fraction)
    assert allocator._calculate_portfolio_heat() == 0.0
