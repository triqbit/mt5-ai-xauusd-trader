import pytest
from src.trading.capital_allocator import CapitalAllocator, StrategyConfig

@pytest.fixture
def allocator():
    configs = {
        "strat_a": StrategyConfig(
            name="strat_a",
            capital_cap=100000, # Large cap
            base_weight=0.5,
            correlation_group="gold",
            max_heat=0.50 # Large heat limit
        ),
        "strat_b": StrategyConfig(
            name="strat_b",
            capital_cap=100000,
            base_weight=0.3,
            correlation_group="fx",
            max_heat=0.50
        ),
        "strat_c": StrategyConfig(
            name="strat_c",
            capital_cap=100000,
            base_weight=0.2,
            correlation_group="gold",
            max_heat=0.50
        )
    }
    return CapitalAllocator(
        total_capital=100000,
        configs=configs,
        max_portfolio_heat=0.50, # Large portfolio heat limit
        max_group_concentration=0.60
    )

def test_basic_allocation(allocator):
    # Request 1000 capital with 100 risk
    res = allocator.get_allocation("strat_a", 1000, 100)
    assert res.approved is True
    assert res.allocated_amount == 1000

def test_strategy_cap(allocator):
    # Override strat_b config to have small cap for this test
    allocator.configs["strat_b"].capital_cap = 5000

    # Allocate 4500
    allocator.allocate("strat_b", 4500, 50)

    # Request another 1000
    res = allocator.get_allocation("strat_b", 1000, 10)
    assert res.approved is True
    assert res.allocated_amount == 500 # Scaled down to cap

    # Allocate the rest
    allocator.allocate("strat_b", 500, 5)

    # Request more
    res = allocator.get_allocation("strat_b", 100, 1)
    assert res.approved is False
    assert "cap reached" in res.reason

def test_strategy_heat_limit(allocator):
    # Set strat_a heat limit to 2000 risk
    allocator.configs["strat_a"].max_heat = 0.02

    # Request 3000 risk with 30000 capital
    res = allocator.get_allocation("strat_a", 30000, 3000)
    assert res.approved is True
    # Scaled down to 2000 risk -> 2/3 ratio. 30000 * 2/3 = 20000
    assert res.allocated_amount == pytest.approx(20000)

def test_portfolio_heat_limit(allocator):
    # Set max portfolio heat to 0.10 of 100k = 10000 risk
    allocator.max_portfolio_heat = 0.10

    # Allocate 8000 risk to strat_a. Total heat = 8000.
    allocator.allocate("strat_a", 80000, 8000)

    # Request 4000 risk for strat_b (fx group).
    # Total heat would be 12000 > 10000.
    # Group concentration for fx: 4000/12000 = 33% < 60%.

    res = allocator.get_allocation("strat_b", 4000, 4000)
    assert res.approved is True
    # Available portfolio risk = 10000 - 8000 = 2000.
    # 2000/4000 = 0.5 ratio. 4000 * 0.5 = 2000.
    assert res.allocated_amount == pytest.approx(2000)

def test_group_concentration(allocator):
    # Allocate 6000 risk to strat_b (fx group).
    # Total heat = 6000 (> 5000 significant).
    allocator.allocate("strat_b", 60000, 6000)

    # Request 10000 risk for strat_a (gold)
    # Total heat would be 16000. Gold group heat would be 10000.
    # 10000/16000 = 62.5% > 60%.
    # Portfolio heat limit is 0.50 of 100k = 50000. 16000 < 50000.

    res = allocator.get_allocation("strat_a", 10000, 10000)
    assert res.approved is True
    # allowed_x = (0.6 * 6000 - 0) / (1 - 0.6) = 3600 / 0.4 = 9000.
    assert res.allocated_amount == pytest.approx(9000)

def test_adaptive_budgeting(allocator):
    # Initial multiplier is 1.0
    res = allocator.get_allocation("strat_a", 1000, 100)
    assert res.allocated_amount == 1000

    # Record a loss
    allocator.update_performance("strat_a", -500)
    # Multiplier becomes 0.9
    res = allocator.get_allocation("strat_a", 1000, 100)
    assert res.allocated_amount == pytest.approx(900)

    # Record a win
    allocator.update_performance("strat_a", 200)
    # Multiplier becomes 0.95
    res = allocator.get_allocation("strat_a", 1000, 100)
    assert res.allocated_amount == pytest.approx(950)

def test_release_capital(allocator):
    allocator.allocate("strat_a", 5000, 500)
    assert allocator.strategy_capital_used["strat_a"] == 5000

    allocator.release("strat_a", 5000, 500)
    assert allocator.strategy_capital_used["strat_a"] == 0
    assert allocator.strategy_heat["strat_a"] == 0
