"""Tests for src.trading.risk_manager module."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.core.config import TradingConfig
from src.trading.risk_manager import RiskManager, TradeSignal


@pytest.fixture
def config() -> TradingConfig:
    """Fixture for TradingConfig."""
    cfg = MagicMock(spec=TradingConfig)
    cfg.risk_per_trade = 0.01
    cfg.max_daily_loss = 0.05
    cfg.max_positions = 3
    cfg.algorithm = "ensemble"
    return cfg


@pytest.fixture
def risk_manager(config: TradingConfig) -> RiskManager:
    """Fixture for RiskManager."""
    return RiskManager(config, account_balance=10000.0)


def test_approve_signal_valid(risk_manager: RiskManager) -> None:
    """Test approval of a valid signal."""
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8,
        timestamp=datetime.now(),
    )
    assert risk_manager.approve(signal) is True


def test_approve_signal_invalid_symbol(risk_manager: RiskManager) -> None:
    """Test rejection of a signal with an invalid symbol."""
    signal = TradeSignal(
        symbol="INVALID",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8,
        timestamp=datetime.now(),
    )
    assert risk_manager.approve(signal) is False


def test_risk_reward_ratio(risk_manager: RiskManager) -> None:
    """Test risk-reward ratio check."""
    # Entry 2000, SL 1995 (Risk 5), TP 2005 (Reward 5) -> R:R 1.0 (min 1.5)
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1995.0,
        take_profit=2005.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8,
        timestamp=datetime.now(),
    )
    assert risk_manager.approve(signal) is False


def test_update_equity(risk_manager: RiskManager) -> None:
    """Test update_equity."""
    risk_manager.update_equity(11000.0)
    assert risk_manager.balance == 11000.0
    assert risk_manager.peak_equity == 11000.0
    assert risk_manager.daily.peak_equity == 11000.0


def test_reset_daily(risk_manager: RiskManager) -> None:
    """Test reset_daily."""
    risk_manager.record_pnl(500.0)
    risk_manager.monitor = MagicMock()
    risk_manager.reset_daily()
    assert risk_manager.daily.realised_pnl == 0.0
    risk_manager.monitor.send_daily_summary.assert_called_once()


def test_approve_signal_low_confidence(risk_manager: RiskManager) -> None:
    """Test rejection of a signal with low confidence."""
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.4,
        timestamp=datetime.now(),
    )
    assert risk_manager.approve(signal) is False


def test_calculate_position_size(risk_manager: RiskManager) -> None:
    """Test position size calculation."""
    size = risk_manager.size_position(
        symbol="XAUUSD",
        win_rate=0.6,
        avg_win=2.0,
        avg_loss=1.0,
        pip_value=1.0,
    )
    assert size > 0
    assert size <= 30.0


def test_circuit_breaker(risk_manager: RiskManager) -> None:
    """Test circuit breaker trigger."""
    risk_manager.update_equity(8000.0)  # 20% drawdown
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8,
        timestamp=datetime.now(),
    )
    assert risk_manager.approve(signal) is False


def test_daily_loss_limit(risk_manager: RiskManager) -> None:
    """Test daily loss limit trigger."""
    risk_manager.record_pnl(-600.0)  # 6% loss
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8,
        timestamp=datetime.now(),
    )
    assert risk_manager.approve(signal) is False


def test_max_positions(risk_manager: RiskManager) -> None:
    """Test max positions limit."""
    risk_manager.open_positions = {"S1": 1, "S2": 2, "S3": 3}
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8,
        timestamp=datetime.now(),
    )
    assert risk_manager.approve(signal) is False
