"""
MT5 AI/ML Trading Bot - Institutional Feedback Loop Integration Test
tests/test_institutional_feedback_loop.py

Verifies the high-value system path:
Capital Allocation -> Execution Logging -> Performance Feedback -> Risk Adaptation -> Audit Traceability
"""

import uuid

import pytest
import structlog
from sqlalchemy import select

from src.core.audit_log import AuditEntry, AuditLogger
from src.core.trade_logger import TradeLogger
from src.trading.capital_allocator import CapitalAllocator, StrategyConfig


@pytest.fixture
def system_env(tmp_path):
    """Sets up a temporary environment for feedback loop testing."""
    # We use in-memory for speed and isolation
    audit_db_url = "sqlite:///:memory:"
    trade_db_url = "sqlite:///:memory:"

    # Initialize loggers
    AuditLogger._instance = None
    AuditLogger._initialized = False
    audit_logger = AuditLogger(db_url=audit_db_url)
    trade_logger = TradeLogger(db_url=trade_db_url)

    # Configure structlog for trace correlation
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.JSONRenderer(),
        ]
    )

    yield audit_logger, trade_logger


def test_institutional_feedback_loop_end_to_end(system_env):
    """
    Test Path: Allocation -> Trade -> Feedback -> Adaptation -> Audit
    """
    audit_logger, trade_logger = system_env

    # 1. Initialize Allocator
    allocator = CapitalAllocator(
        total_budget=10000.0,
        performance_step=0.1,  # Fast adaptation for testing
        decay_rate=0.0,
    )

    strat_id = "ENSEMBLE_XAUUSD_M5"
    allocator.add_strategy(
        StrategyConfig(
            strategy_id=strat_id, symbol="XAUUSD", model_family="ENSEMBLE", capital_cap=5000.0
        )
    )

    # 2. First Allocation Request (Baseline)
    trace_id_1 = str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(trace_id=trace_id_1)

    res1 = allocator.request_allocation(strat_id, risk_pct=0.01)
    assert res1.is_allowed is True
    assert res1.allocated_risk_pct == 0.01
    assert res1.allocated_amount == 100.0

    # 3. Simulate Trade Execution and Profit Feedback
    ticket_win = 100001
    trade_logger.log_trade(
        ticket=ticket_win,
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        lot_size=0.1,
        status="OPEN",
    )

    # Close with $200 profit
    trade_logger.update_trade(ticket=ticket_win, exit_price=2020.0)
    updated_trade_win = trade_logger.get_trade_by_ticket(ticket_win)
    assert updated_trade_win.pnl == 200.0

    # Apply Feedback
    allocator.update_strategy_performance(strat_id, updated_trade_win.pnl)
    assert allocator.strategies[strat_id].performance_multiplier == 1.1

    # 4. Second Allocation Request (Expect increase)
    trace_id_2 = str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(trace_id=trace_id_2)

    res2 = allocator.request_allocation(strat_id, risk_pct=0.01)
    assert res2.is_allowed is True
    assert res2.was_scaled is True
    assert res2.allocated_risk_pct == pytest.approx(0.011)  # 0.01 * 1.1
    assert res2.allocated_amount == pytest.approx(110.0)

    # 5. Simulate Loss Feedback and Cooling-off
    ticket_loss = 100002
    trade_logger.log_trade(
        ticket=ticket_loss,
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        lot_size=0.1,
        status="OPEN",
    )

    # StrategyConfig default max_consecutive_losses is 5.
    # We'll force consecutive losses.
    for _ in range(5):
        allocator.update_strategy_performance(strat_id, -100.0)

    # Multiplier should have dropped: 1.1 -> 1.0 -> 0.9 -> 0.8 -> 0.7 -> 0.6
    # BUT cooling off triggers at 5 losses, floor becomes 0.1
    assert allocator.strategies[strat_id].consecutive_losses >= 5
    assert allocator.strategies[strat_id].performance_multiplier == 0.1

    # 6. Third Allocation Request (Expect significant reduction)
    res3 = allocator.request_allocation(strat_id, risk_pct=0.01)
    assert res3.allocated_risk_pct == pytest.approx(0.001)  # 0.01 * 0.1

    # 7. Verify Audit Trail
    with audit_logger.Session() as session:
        # Verify allocation decisions
        alloc_decisions = (
            session.execute(
                select(AuditEntry)
                .where(AuditEntry.action == "allocation_decision")
                .order_by(AuditEntry.id)
            )
            .scalars()
            .all()
        )
        assert len(alloc_decisions) >= 3
        assert alloc_decisions[0].trace_id == trace_id_1
        assert alloc_decisions[1].trace_id == trace_id_2

        # Verify config changes (performance adjustments)
        config_changes = (
            session.execute(select(AuditEntry).where(AuditEntry.action == "config_change"))
            .scalars()
            .all()
        )
        assert len(config_changes) >= 1
        assert config_changes[0].metadata_json["new"]["multiplier"] == 1.1
