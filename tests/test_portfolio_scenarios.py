"""
Integration tests for PortfolioScenarioBuilder and CapitalAllocator.
"""
import pytest

from src.trading.capital_allocator import CapitalAllocator, RejectionCode, StrategyConfig
from src.utils.synthetic_data import PortfolioScenarioBuilder


@pytest.fixture
def builder():
    return PortfolioScenarioBuilder(seed=42)

@pytest.fixture
def allocator():
    return CapitalAllocator(
        total_budget=100000.0,
        max_symbol_risk=0.4,
        max_family_risk=0.4,
        max_total_heat=0.7,
        performance_step=0.1,
        soft_limit_buffer=0.0  # Disable soft buffer for deterministic hard limit testing
    )

def test_concentration_risk_cascade(builder, allocator):
    configs, requests = builder.concentration_risk_cascade()
    for cfg in configs:
        allocator.add_strategy(cfg)

    # First two gold strategies should pass (0.15 + 0.15 = 0.3)
    res1 = allocator.request_allocation(requests[0].strategy_id, requests[0].risk_pct)
    assert res1.is_allowed is True
    allocator.update_allocation(res1.strategy_id, res1.allocated_amount)

    res2 = allocator.request_allocation(requests[1].strategy_id, requests[1].risk_pct)
    assert res2.is_allowed is True
    allocator.update_allocation(res2.strategy_id, res2.allocated_amount)

    # Third gold strategy should hit symbol limit (0.3 + 0.15 = 0.45 > 0.4)
    res3 = allocator.request_allocation(requests[2].strategy_id, requests[2].risk_pct)
    assert res3.is_allowed is False
    assert res3.rejection_code == RejectionCode.SYMBOL_CONCENTRATION_LIMIT

    # Fourth strategy (EURUSD) should hit family limit (RL family already has 0.3 from gold_rl_1/2)
    # 0.3 + 0.15 = 0.45 > 0.4
    res4 = allocator.request_allocation(requests[3].strategy_id, requests[3].risk_pct)
    assert res4.is_allowed is False
    assert res4.rejection_code == RejectionCode.FAMILY_CONCENTRATION_LIMIT

def test_performance_rebalancing_sequence(builder, allocator):
    sequence = builder.performance_rebalancing_sequence()

    allocator.add_strategy(StrategyConfig(
        strategy_id="strat_a",
        symbol="XAUUSD",
        model_family="RL",
        capital_cap=100000,
        max_consecutive_losses=3,
    ))

    results = []
    for step in sequence:
        # 1. Request
        res = allocator.request_allocation(step["strategy_id"], step["request"])
        results.append(res)
        # 2. Update performance
        allocator.update_strategy_performance(step["strategy_id"], step["pnl"])

    # First request should be baseline (0.02)
    assert results[0].allocated_risk_pct == 0.02

    # After two wins, multiplier should be 1.2
    # Result 2 (3rd step) should be scaled
    assert results[2].allocated_risk_pct == pytest.approx(0.02 * 1.2)

    # Last step should show cooling off impact if we checked it after 3 losses.
    # In the sequence: Win, Win, Loss, Loss, Loss.
    # Consecutive losses hits 3 at the end of the 5th step.
    # So the 5th request happened when consecutive_losses was 2.
    assert allocator.strategies["strat_a"].consecutive_losses == 3
    assert allocator.strategies["strat_a"].performance_multiplier == 0.1

def test_high_heat_portfolio(builder, allocator):
    configs, requests = builder.high_heat_portfolio()
    for cfg in configs:
        allocator.add_strategy(cfg)

    # Request until heat limit (0.7)
    # 0.15 * 4 = 0.6. 5th request makes it 0.75.
    for i in range(4):
        res = allocator.request_allocation(requests[i].strategy_id, requests[i].risk_pct)
        assert res.is_allowed is True
        allocator.update_allocation(res.strategy_id, res.allocated_amount)

    final_res = allocator.request_allocation(requests[4].strategy_id, requests[4].risk_pct)
    assert final_res.is_allowed is False
    assert final_res.rejection_code == RejectionCode.TOTAL_HEAT_LIMIT

def test_diversified_unbalanced_setup(builder, allocator):
    configs = builder.diversified_unbalanced_setup()
    for cfg in configs:
        allocator.add_strategy(cfg)
        # Simulate some allocation
        allocator.update_allocation(cfg.strategy_id, 10000.0)

    score = allocator.get_diversification_score()
    # 3 strategies with equal allocation (10k each) should have score 1.0
    assert score == pytest.approx(1.0)

    # Unbalance it
    allocator.update_allocation("alpha", 80000.0)
    new_score = allocator.get_diversification_score()
    assert new_score < 1.0
