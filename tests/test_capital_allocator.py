"""
Unit tests for CapitalAllocator.
"""

import pytest
from src.trading.capital_allocator import CapitalAllocator, AllocationRequest


def test_capital_allocator_initialization():
    allocator = CapitalAllocator(total_equity=10000.0)
    assert allocator.equity == 10000.0
    assert allocator.max_heat_pct == 0.20
    assert allocator.symbol_limit_pct == 0.50


def test_strategy_registration():
    allocator = CapitalAllocator(total_equity=10000.0)
    allocator.register_strategy("ensemble", capital_cap_pct=0.4)
    assert "ensemble" in allocator.strategies
    assert allocator.strategies["ensemble"].capital_cap == 4000.0


def test_successful_allocation():
    allocator = CapitalAllocator(total_equity=10000.0)
    allocator.register_strategy("ensemble", capital_cap_pct=0.4)

    request = AllocationRequest(
        strategy_id="ensemble",
        symbol="XAUUSD",
        requested_risk=200.0,
        confidence=1.0
    )

    result = allocator.request_allocation(request)
    assert result.approved is True
    assert result.allocated_risk == 200.0


def test_global_heat_limit():
    allocator = CapitalAllocator(total_equity=10000.0, global_max_heat=0.01) # $100 max risk
    allocator.register_strategy("ensemble", capital_cap_pct=0.5)

    request = AllocationRequest(
        strategy_id="ensemble",
        symbol="XAUUSD",
        requested_risk=150.0,
        confidence=1.0
    )

    result = allocator.request_allocation(request)
    assert result.approved is False
    assert "Global portfolio heat limit exceeded" in result.reason


def test_symbol_concentration_limit():
    # equity=10000, heat=20% ($2000), symbol_limit=50% ($1000)
    allocator = CapitalAllocator(total_equity=10000.0)
    allocator.register_strategy("ensemble", capital_cap_pct=0.5)

    # Commit some risk to XAUUSD
    allocator.commit_allocation("ensemble", "XAUUSD", 900.0)

    request = AllocationRequest(
        strategy_id="ensemble",
        symbol="XAUUSD",
        requested_risk=200.0,
        confidence=1.0
    )

    result = allocator.request_allocation(request)
    assert result.approved is False
    assert "concentration limit exceeded" in result.reason


def test_strategy_cap_limit():
    allocator = CapitalAllocator(total_equity=10000.0)
    allocator.register_strategy("ensemble", capital_cap_pct=0.05) # $500 cap

    allocator.commit_allocation("ensemble", "XAUUSD", 450.0)

    request = AllocationRequest(
        strategy_id="ensemble",
        symbol="XAUUSD",
        requested_risk=100.0,
        confidence=1.0
    )

    result = allocator.request_allocation(request)
    assert result.approved is False
    assert "capital cap reached" in result.reason


def test_adaptive_budgeting():
    allocator = CapitalAllocator(total_equity=10000.0)
    allocator.register_strategy("ensemble", capital_cap_pct=0.5)

    # 60% win rate -> multiplier = 0.6 / 0.5 = 1.2
    allocator.update_performance("ensemble", 0.60)

    request = AllocationRequest(
        strategy_id="ensemble",
        symbol="XAUUSD",
        requested_risk=100.0,
        confidence=1.0
    )

    result = allocator.request_allocation(request)
    assert result.approved is True
    assert result.allocated_risk == 120.0 # 100 * 1.2


def test_release_allocation():
    allocator = CapitalAllocator(total_equity=10000.0)
    allocator.register_strategy("ensemble", capital_cap_pct=0.5)

    allocator.commit_allocation("ensemble", "XAUUSD", 500.0)
    assert allocator.symbol_heat["XAUUSD"] == 500.0

    allocator.release_allocation("ensemble", "XAUUSD", 500.0)
    assert allocator.symbol_heat["XAUUSD"] == 0.0
    assert allocator.strategies["ensemble"].current_used == 0.0


def test_limit_enforcement_after_multiplier():
    """Verify that limits are enforced AFTER performance multipliers are applied."""
    allocator = CapitalAllocator(total_equity=10000.0, global_max_heat=0.01) # $100 max risk
    allocator.register_strategy("ensemble", capital_cap_pct=0.5)

    # High performance -> 1.5x multiplier
    allocator.update_performance("ensemble", 0.75)

    # Request $80 risk. $80 < $100 (limit), but 1.5x * $80 = $120 > $100.
    request = AllocationRequest(
        strategy_id="ensemble",
        symbol="XAUUSD",
        requested_risk=80.0,
        confidence=1.0
    )

    result = allocator.request_allocation(request)
    assert result.approved is False
    assert "Global portfolio heat limit exceeded" in result.reason


def test_update_equity_rescales_caps():
    allocator = CapitalAllocator(total_equity=10000.0)
    allocator.register_strategy("ensemble", capital_cap_pct=0.5) # $5000
    assert allocator.strategies["ensemble"].capital_cap == 5000.0

    allocator.update_equity(20000.0)
    assert allocator.strategies["ensemble"].capital_cap == 10000.0


def test_commit_allocation_increments_trades():
    allocator = CapitalAllocator(total_equity=10000.0)
    allocator.register_strategy("ensemble", capital_cap_pct=0.5)
    assert allocator.strategies["ensemble"].trades_count == 0

    allocator.commit_allocation("ensemble", "XAUUSD", 100.0)
    assert allocator.strategies["ensemble"].trades_count == 1
