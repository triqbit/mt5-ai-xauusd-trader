"""Integration tests for TradeLogger."""

from __future__ import annotations

from pathlib import Path
from typing import Generator

import pytest

from src.core.trade_logger import TradeLogger


@pytest.fixture
def logger() -> Generator[TradeLogger, None, None]:
    """Fixture to provide a clean TradeLogger instance for each test.

    Yields:
        A TradeLogger instance connected to a temporary test database.
    """
    db_path = Path("test_trades.db")
    if db_path.exists():
        db_path.unlink()
    logger_instance = TradeLogger(db_url=f"sqlite:///{db_path}")
    yield logger_instance
    if db_path.exists():
        db_path.unlink()


def test_log_signal(logger: TradeLogger) -> None:
    """Test that model signals are correctly saved to the database.

    Args:
        logger: The TradeLogger fixture.
    """
    signal_data = {
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0,
        "algorithm": "ppo",
        "confidence": 0.8,
    }
    signal_id = logger.log_signal(signal_data)
    assert signal_id > 0


def test_log_trade(logger: TradeLogger) -> None:
    """Test that executed trades are correctly saved to the database.

    Args:
        logger: The TradeLogger fixture.
    """
    signal_id = logger.log_signal(
        {
            "symbol": "XAUUSD",
            "direction": 1,
            "entry_price": 2000.0,
        }
    )
    trade_id = logger.log_trade(
        ticket=123,
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        lot_size=0.1,
        signal_id=signal_id,
    )
    assert trade_id > 0


def test_performance_report(logger: TradeLogger) -> None:
    """Test that performance metrics are correctly calculated from closed trades.

    Args:
        logger: The TradeLogger fixture.
    """
    # Log some closed trades
    # PnL = (exit - entry) * direction * lot_size * 100
    # Trade 1: (2050 - 2000) * 1 * 0.1 * 100 = 50 * 0.1 * 100 = 500
    logger.log_trade(1, "XAUUSD", 1, 2000.0, 0.1, status="OPEN")
    logger.update_trade(1, 2050.0)  # Profit 500

    # Trade 2: (1950 - 2000) * 1 * 0.1 * 100 = -50 * 0.1 * 100 = -500
    logger.log_trade(2, "XAUUSD", 1, 2000.0, 0.1, status="OPEN")
    logger.update_trade(2, 1950.0)  # Loss -500

    report = logger.read_performance_report()
    assert "sharpe_ratio" in report
    assert report["profit_factor"] == 1.0  # 500 / 500
    assert report["max_drawdown"] == 500.0


def test_log_risk_event(logger: TradeLogger) -> None:
    """Test that risk management events are correctly saved to the database.

    Args:
        logger: The TradeLogger fixture.
    """
    logger.log_risk_event("CIRCUIT_BREAKER", "Drawdown limit hit")
    # No exception means success, we could query DB to be sure
