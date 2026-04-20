"""
Unit tests for src/trading/risk_manager.py
Step 5: Test Coverage (PHASE1_ROADMAP)
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.trading.risk_manager import (
    ALLOCATION_WEIGHTS,
    DailyStats,
    RiskManager,
    TradeSignal,
)


@pytest.fixture
def config() -> MagicMock:
    """Minimal TradingConfig mock."""
    cfg = MagicMock()
    cfg.risk_per_trade = 0.02
    cfg.max_daily_loss = 0.05
    cfg.max_positions = 3
    return cfg


@pytest.fixture
def risk_manager(config: MagicMock) -> RiskManager:
    return RiskManager(config=config, account_balance=10_000.0)


@pytest.fixture
def valid_signal() -> TradeSignal:
    return TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="PPO",
        confidence=0.75,
        timestamp=datetime.utcnow(),
    )


# ---------------------------------------------------------------------------
# ALLOCATION_WEIGHTS
# ---------------------------------------------------------------------------

class TestAllocationWeights:
    def test_xauusd_present(self) -> None:
        assert "XAUUSD" in ALLOCATION_WEIGHTS

    def test_weights_sum_to_one(self) -> None:
        total = sum(ALLOCATION_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01

    def test_all_weights_positive(self) -> None:
        for symbol, weight in ALLOCATION_WEIGHTS.items():
            assert weight > 0, f"{symbol} has non-positive weight"


# ---------------------------------------------------------------------------
# RiskManager initialisation
# ---------------------------------------------------------------------------

class TestRiskManagerInit:
    def test_balance_set(self, risk_manager: RiskManager) -> None:
        assert risk_manager.balance == 10_000.0

    def test_peak_equity_equals_balance(self, risk_manager: RiskManager) -> None:
        assert risk_manager.peak_equity == 10_000.0

    def test_open_positions_empty(self, risk_manager: RiskManager) -> None:
        assert risk_manager.open_positions == {}


# ---------------------------------------------------------------------------
# approve() -- 6-layer filter
# ---------------------------------------------------------------------------

class TestApprove:
    def test_valid_signal_approved(self, risk_manager: RiskManager, valid_signal: TradeSignal) -> None:
        assert risk_manager.approve(valid_signal) is True

    def test_circuit_breaker_blocks(self, risk_manager: RiskManager, valid_signal: TradeSignal) -> None:
        # Simulate 20% drawdown
        risk_manager.balance = 8_000.0
        assert risk_manager.approve(valid_signal) is False

    def test_max_positions_blocks(self, risk_manager: RiskManager, valid_signal: TradeSignal) -> None:
        risk_manager.open_positions = {"XAUUSD": 1, "EURUSD": 2, "GBPUSD": 3}
        assert risk_manager.approve(valid_signal) is False

    def test_unknown_symbol_blocked(self, risk_manager: RiskManager, valid_signal: TradeSignal) -> None:
        valid_signal.symbol = "BTCUSD"
        assert risk_manager.approve(valid_signal) is False

    def test_low_confidence_blocked(self, risk_manager: RiskManager, valid_signal: TradeSignal) -> None:
        valid_signal.confidence = 0.40
        assert risk_manager.approve(valid_signal) is False

    def test_bad_risk_reward_blocked(self, risk_manager: RiskManager, valid_signal: TradeSignal) -> None:
        # entry=2000, stop=1999 (1pt risk), tp=2001 (1pt reward) -> RR=1.0 < 1.5
        valid_signal.stop_loss = 1999.0
        valid_signal.take_profit = 2001.0
        assert risk_manager.approve(valid_signal) is False

    def test_daily_loss_limit_blocks(self, risk_manager: RiskManager, valid_signal: TradeSignal) -> None:
        risk_manager.daily.realised_pnl = -600.0  # 6% > 5% limit
        assert risk_manager.approve(valid_signal) is False


# ---------------------------------------------------------------------------
# size_position() -- Kelly Criterion
# ---------------------------------------------------------------------------

class TestSizePosition:
    def test_zero_avg_loss_returns_minimum(self, risk_manager: RiskManager) -> None:
        lot = risk_manager.size_position("XAUUSD", 0.6, 100.0, 0.0)
        assert lot == 0.01

    def test_returns_positive_lot(self, risk_manager: RiskManager) -> None:
        lot = risk_manager.size_position("XAUUSD", 0.6, 100.0, 50.0)
        assert lot > 0

    def test_lot_minimum_is_001(self, risk_manager: RiskManager) -> None:
        lot = risk_manager.size_position("XAUUSD", 0.01, 1.0, 1000.0)
        assert lot >= 0.01


# ---------------------------------------------------------------------------
# update_equity() and record_pnl()
# ---------------------------------------------------------------------------

class TestEquityAndPnl:
    def test_update_equity_updates_balance(self, risk_manager: RiskManager) -> None:
        risk_manager.update_equity(11_000.0)
        assert risk_manager.balance == 11_000.0

    def test_update_equity_tracks_peak(self, risk_manager: RiskManager) -> None:
        risk_manager.update_equity(12_000.0)
        risk_manager.update_equity(11_000.0)
        assert risk_manager.peak_equity == 12_000.0

    def test_record_pnl_accumulates(self, risk_manager: RiskManager) -> None:
        risk_manager.record_pnl(100.0)
        risk_manager.record_pnl(200.0)
        assert risk_manager.daily.realised_pnl == 300.0
        assert risk_manager.daily.trade_count == 2

    def test_reset_daily_clears_stats(self, risk_manager: RiskManager) -> None:
        risk_manager.record_pnl(-500.0)
        risk_manager.reset_daily()
        assert risk_manager.daily.realised_pnl == 0.0
        assert risk_manager.daily.trade_count == 0
