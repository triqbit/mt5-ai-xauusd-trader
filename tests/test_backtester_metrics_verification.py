"""
Deterministic metrics verification for BacktestEngine.
Verifies transaction costs (spread + commission) and MAE/MFE.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import pytest
from unittest.mock import MagicMock

from src.trading.backtester import BacktestEngine, BacktestTrade
from src.core.schemas import TradeSignal

class SimpleModel:
    def __init__(self, direction=1):
        self.direction = direction
    def predict(self, obs):
        return type("Signal", (), {"direction": self.direction, "confidence": 0.9})

def test_pnl_calculation():
    """Manual verification of _record_trade PnL logic."""
    spread = 2.0
    commission = 7.0
    engine = BacktestEngine(
        symbol="XAUUSD",
        spread=spread,
        commission_per_lot=commission,
        initial_balance=10000.0
    )

    # BUY trade
    # entry_price_adj = entry_price + (direction * spread / 2)
    # exit_price_adj = exit_price - (direction * spread / 2)
    entry_price = 2000.0
    exit_price = 2020.0
    direction = 1
    lot_size = 0.1

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=direction,
        entry_price=entry_price,
        stop_loss=1990.0,
        take_profit=2030.0,
        lot_size=lot_size,
        algorithm="test",
        confidence=0.9
    )

    trade_data = {
        "signal": signal,
        "entry_price": entry_price + (direction * spread / 2),
        "mae": 5.0,
        "mfe": 15.0,
        "exit_abs_idx": 10
    }

    engine._record_trade(trade_data, exit_price, datetime.now())

    trade = engine.trades[0]
    expected_entry = 2001.0
    expected_exit = 2019.0 # 2020 - (1 * 2/2)
    expected_raw_pnl = (expected_exit - expected_entry) * lot_size * 100 # XAUUSD multiplier
    expected_final_pnl = expected_raw_pnl - (lot_size * commission) # 18 * 0.1 * 100 - 0.7 = 180 - 0.7 = 179.3

    assert trade.entry_price == expected_entry
    assert trade.exit_price == expected_exit
    assert trade.pnl == pytest.approx(expected_final_pnl)
    assert engine.balance == pytest.approx(10000.0 + expected_final_pnl)

def test_mae_mfe_simulation_logic():
    """Verifies MAE/MFE calculation in _open_and_simulate_trade."""
    engine = BacktestEngine(symbol="XAUUSD", spread=2.0)

    # BUY Signal at index 0
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1980.0,
        take_profit=2050.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.9
    )

    high_vals = np.array([2000.0, 2010.0, 2005.0, 2060.0])
    low_vals = np.array([2000.0, 1990.0, 1995.0, 2040.0])
    time_vals = pd.date_range("2024-01-01", periods=4, freq="5min")

    active_trades = []
    engine._open_and_simulate_trade(active_trades, signal, 0, high_vals, low_vals, time_vals)

    assert len(active_trades) == 1
    t = active_trades[0]

    # Entry Price Adj = 2000 + 1.0 = 2001.0
    # Future bars: 1, 2, 3
    # Bar 1: H=2010, L=1990
    # Bar 2: H=2005, L=1995
    # Bar 3: H=2060, L=2040 -> TP Hit (2050)

    # MAE = Entry(2001) - MinLow(Bar 1: 1990, Bar 2: 1995, Bar 3: 2040) = 2001 - 1990 = 11.0
    assert t["mae"] == pytest.approx(11.0)
    # MFE = MaxHigh(Bar 1: 2010, Bar 2: 2005, Bar 3: 2060) - Entry(2001) = 2060 - 2001 = 59.0
    assert t["mfe"] == pytest.approx(59.0)
    assert t["exit_abs_idx"] == 3
    assert t["exit_price"] == 2050.0
