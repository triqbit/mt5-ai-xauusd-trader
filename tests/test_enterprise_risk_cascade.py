"""
MT5 AI/ML Trading Bot - Enterprise Risk Cascade Integration Test
tests/test_enterprise_risk_cascade.py

Verifies the high-value system paths:
1. Capital Allocation -> Risk Sizing -> Lot Calculation (Scaling Cascade)
2. Database Persistence -> Risk State Recovery (Reconciliation Cascade)
"""

from unittest.mock import MagicMock

import pytest

from src.core.audit_log import AuditLogger
from src.core.schemas import TradeSignal
from src.core.trade_logger import TradeLogger
from src.trading.audited_risk_manager import AuditedRiskManager
from src.trading.capital_allocator import CapitalAllocator, StrategyConfig


@pytest.fixture
def system_paths(tmp_path):
    db_path = tmp_path / "risk_test.db"
    audit_db_path = tmp_path / "audit_test.db"
    return str(db_path), str(audit_db_path)

@pytest.fixture
def mock_cfg():
    cfg = MagicMock()
    cfg.risk_per_trade = 0.02
    cfg.max_positions = 5
    cfg.max_losing_streak = 3
    cfg.max_daily_loss = 0.05
    cfg.model_drift_threshold = 0.3
    cfg.model_accuracy_floor = 0.45
    cfg.model_calibration_threshold = 0.2
    cfg.symbol = "XAUUSD"
    return cfg

def test_risk_scaling_cascade(mock_cfg, system_paths):
    """
    Path: CapitalAllocator (Scales Risk) -> RiskManager (Calculates Lot)
    Verifies that when the allocator reduces risk (e.g. symbol limit),
    the position sizing correctly reflects the reduced risk.
    """
    db_path, audit_db_path = system_paths

    # Initialize AuditLogger for AuditedRiskManager
    AuditLogger._instance = None
    AuditLogger._initialized = False
    AuditLogger(db_url=f"sqlite:///{audit_db_path}")

    trade_logger = TradeLogger(db_url=f"sqlite:///{db_path}")

    # 1. Setup Allocator with tight symbol limit
    # Total budget 100k, symbol limit 5% (5000), soft buffer 0
    allocator = CapitalAllocator(
        total_budget=100000.0,
        max_symbol_risk=0.05,
        soft_limit_buffer=0.0
    )
    strat_id = "ENSEMBLE_XAUUSD_M5"
    allocator.add_strategy(StrategyConfig(
        strategy_id=strat_id,
        symbol="XAUUSD",
        model_family="ensemble",
        capital_cap=100000.0
    ))

    # 2. Setup RiskManager
    risk_manager = AuditedRiskManager(mock_cfg, account_balance=100000.0, logger_db=trade_logger)

    # 3. Simulate Scenario: Symbol already has 4% risk allocated
    # Register another strategy for the same symbol to take up heat
    allocator.add_strategy(StrategyConfig(
        strategy_id="OTHER", symbol="XAUUSD", model_family="other", capital_cap=100000.0
    ))
    allocator.update_allocation("OTHER", 4000.0) # 4% of 100k

    # 4. Request 2% risk for XAUUSD
    # Limit is 5%, 4% used, only 1% available.
    alloc_res = allocator.request_allocation(strat_id, risk_pct=0.02, allow_scaling=True)
    assert alloc_res.is_allowed is True
    assert alloc_res.allocated_risk_pct == pytest.approx(0.01) # Scaled to 1%
    assert alloc_res.was_capped is True

    # 5. Calculate Lot Size with scaled risk
    # Kelly Params for 25% cap: (0.6*4 - 0.4*2)/4 = 0.4 -> 0.25
    lot_size = risk_manager.size_position(
        symbol="XAUUSD",
        win_rate=0.6,
        avg_win=4.0,
        avg_loss=2.0,
        pip_value=1.0,
        risk_pct=alloc_res.allocated_risk_pct
    )

    # Expected: (100000 * 0.01 * 0.25) / (2.0 * 1.0) = 250 / 2 = 125.0
    assert lot_size == 125.0

    # Compare with default risk (2%)
    lot_size_default = risk_manager.size_position(
        symbol="XAUUSD",
        win_rate=0.6,
        avg_win=4.0,
        avg_loss=2.0,
        pip_value=1.0
    )
    # Expected: (100000 * 0.02 * 0.25) / (2.0 * 1.0) = 500 / 2 = 250.0
    assert lot_size_default == 250.0
    assert lot_size == lot_size_default / 2

def test_risk_state_recovery_cascade(mock_cfg, system_paths):
    """
    Path: TradeLogger (DB) -> RiskManager.reconcile_state()
    Verifies that active positions are recovered after a system restart.
    """
    db_path, audit_db_path = system_paths

    # Initialize AuditLogger
    AuditLogger._instance = None
    AuditLogger._initialized = False
    AuditLogger(db_url=f"sqlite:///{audit_db_path}")

    trade_logger = TradeLogger(db_url=f"sqlite:///{db_path}")

    # 1. Pre-populate database with an open trade
    ticket = 999111
    trade_logger.log_trade(
        ticket=ticket,
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        lot_size=0.1,
        status="OPEN"
    )

    # 2. Initialize fresh RiskManager
    risk_manager = AuditedRiskManager(mock_cfg, account_balance=100000.0, logger_db=trade_logger)
    assert len(risk_manager.open_positions) == 0

    # 3. Trigger reconciliation
    risk_manager.reconcile_state()

    # 4. Verify recovery
    assert "XAUUSD" in risk_manager.open_positions
    assert risk_manager.open_positions["XAUUSD"] == ticket

    # 5. Verify that max_positions filter now respects recovered trade
    mock_cfg.max_positions = 1
    signal = TradeSignal(
        symbol="USDCHF", # Use different approved symbol
        direction=1,
        entry_price=0.91,
        stop_loss=0.90,
        take_profit=0.93,
        lot_size=0.1,
        algorithm="test",
        confidence=0.9
    )

    # Should be rejected because 1/1 position is filled by recovered trade
    # Note: USDCHF is in ALLOCATION_WEIGHTS
    assert risk_manager.approve(signal) is False
