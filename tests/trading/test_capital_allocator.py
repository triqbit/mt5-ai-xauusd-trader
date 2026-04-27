import pytest

from src.trading.capital_allocator import (
    AllocationRequest,
    CapitalAllocator,
    StrategyConfig,
)


@pytest.fixture
def strategies():
    return [
        StrategyConfig(name="ensemble", max_capital_share=0.5, max_risk_per_trade=0.02),
        StrategyConfig(name="scalper", max_capital_share=0.2, max_risk_per_trade=0.01),
    ]


@pytest.fixture
def allocator(strategies):
    return CapitalAllocator(total_equity=100000.0, strategies=strategies)


def test_basic_allocation_approval(allocator):
    request = AllocationRequest(
        strategy_id="ensemble",
        symbol="XAUUSD",
        confidence=0.8,
        suggested_risk=0.02,
        current_stop_loss_dist=10.0,
        pip_value=1.0,
    )
    result = allocator.calculate_allocation(request)

    assert result.approved is True
    # final_risk = 0.02 (suggested) * 0.8 (confidence) = 0.016
    assert result.allocated_risk == pytest.approx(0.016)
    # risk_amount = 100000 * 0.016 = 1600
    # lot_size = 1600 / (10 * 1) = 160
    assert result.lot_size == 160.0
    assert result.portfolio_heat_after == pytest.approx(0.016)


def test_reject_unknown_strategy(allocator):
    request = AllocationRequest(
        strategy_id="unknown",
        symbol="XAUUSD",
        confidence=0.8,
        suggested_risk=0.02,
        current_stop_loss_dist=10.0,
    )
    result = allocator.calculate_allocation(request)
    assert result.approved is False
    assert "Unknown strategy ID" in result.rejection_reason


def test_portfolio_heat_limit(allocator):
    # Register 19% risk across multiple symbols to avoid symbol concentration limit (10%)
    allocator.register_trade("ensemble", "XAUUSD", 9000.0)
    allocator.register_trade("ensemble", "EURUSD", 10000.0)

    request = AllocationRequest(
        strategy_id="ensemble",
        symbol="GBPUSD",
        confidence=0.8,
        suggested_risk=0.02,
        current_stop_loss_dist=10.0,
    )
    # Total heat is 19%, max is 20%.
    # It should still approve but cap the risk to the remaining 1%.
    result = allocator.calculate_allocation(request)
    assert result.approved is True
    assert result.allocated_risk == pytest.approx(0.01)
    assert result.portfolio_heat_after <= 0.2000000001


def test_max_portfolio_heat_reached(allocator):
    allocator.register_trade("ensemble", "XAUUSD", 20000.0)
    request = AllocationRequest(
        strategy_id="ensemble",
        symbol="XAUUSD",
        confidence=0.8,
        suggested_risk=0.01,
        current_stop_loss_dist=10.0,
    )
    result = allocator.calculate_allocation(request)
    assert result.approved is False
    assert "Max portfolio heat reached" in result.rejection_reason


def test_strategy_cap_limit(allocator):
    # scalper has 0.2 max_capital_share (20000.0)
    allocator.register_trade("scalper", "EURUSD", 19500.0)

    request = AllocationRequest(
        strategy_id="scalper",
        symbol="XAUUSD",
        confidence=1.0,
        suggested_risk=0.01,
        current_stop_loss_dist=10.0,
    )
    # Should be capped at remaining 500.0 risk (0.005)
    result = allocator.calculate_allocation(request)
    assert result.approved is True
    assert result.allocated_risk == pytest.approx(0.005)


def test_symbol_concentration_limit(allocator):
    # MAX_SYMBOL_CONCENTRATION is 10% (10000.0)
    allocator.register_trade("ensemble", "XAUUSD", 10000.0)

    request = AllocationRequest(
        strategy_id="scalper",
        symbol="XAUUSD",
        confidence=1.0,
        suggested_risk=0.01,
        current_stop_loss_dist=10.0,
    )
    result = allocator.calculate_allocation(request)
    assert result.approved is False
    assert "Max concentration" in result.rejection_reason


def test_low_confidence_rejection(allocator):
    request = AllocationRequest(
        strategy_id="ensemble",
        symbol="XAUUSD",
        confidence=0.4,
        suggested_risk=0.02,
        current_stop_loss_dist=10.0,
    )
    result = allocator.calculate_allocation(request)
    assert result.approved is False
    assert "Confidence too low" in result.rejection_reason


def test_register_unregister_risk(allocator):
    allocator.register_trade("ensemble", "XAUUSD", 1000.0)
    assert allocator.total_risk == 1000.0
    assert allocator.strategy_risk["ensemble"] == 1000.0
    assert allocator.symbol_risk["XAUUSD"] == 1000.0

    allocator.unregister_trade("ensemble", "XAUUSD", 1000.0)
    assert allocator.total_risk == 0.0
    assert allocator.strategy_risk["ensemble"] == 0.0
    assert allocator.symbol_risk["XAUUSD"] == 0.0


def test_update_equity(allocator):
    allocator.update_equity(200000.0)
    request = AllocationRequest(
        strategy_id="ensemble",
        symbol="XAUUSD",
        confidence=1.0,
        suggested_risk=0.01,
        current_stop_loss_dist=10.0,
    )
    result = allocator.calculate_allocation(request)
    # 200000 * 0.01 = 2000 risk
    # 2000 / 10 = 200 lots
    assert result.lot_size == 200.0
