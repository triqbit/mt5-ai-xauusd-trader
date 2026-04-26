"""
Unit tests for the ExecutionFilter cascade.
"""
from datetime import datetime, time
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from src.trading.execution_filter import ExecutionFilter
from src.trading.risk_manager import TradeSignal


@pytest.fixture
def config():
    cfg = MagicMock()
    cfg.mode = "demo"
    return cfg


@pytest.fixture
def execution_filter(config):
    return ExecutionFilter(config, timeframe="M5")


@pytest.fixture
def mock_df():
    # Create 50 bars of data
    df = pd.DataFrame({
        "M5_atr_14": np.linspace(1.0, 1.0, 50),
        "M5_ema_50": np.linspace(100, 105, 50),
        "M5_ema_20": np.linspace(102, 107, 50),
        "M5_ema_200": np.linspace(90, 95, 50),
        "M5_rsi_14": np.linspace(60, 65, 50),
    })
    return df


@pytest.fixture
def buy_signal():
    return TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1980.0,
        take_profit=2050.0,
        lot_size=0.1,
        algorithm="ppo",
        confidence=0.7
    )


@pytest.fixture
def sell_signal():
    return TradeSignal(
        symbol="XAUUSD",
        direction=-1,
        entry_price=2000.0,
        stop_loss=2020.0,
        take_profit=1950.0,
        lot_size=0.1,
        algorithm="ppo",
        confidence=0.7
    )


def test_validate_atr_pass(execution_filter, mock_df):
    assert bool(execution_filter._validate_atr(mock_df)) is True


def test_validate_atr_fail(execution_filter, mock_df):
    # Spiking ATR to 5x the average
    mock_df.loc[49, "M5_atr_14"] = 10.0
    assert bool(execution_filter._validate_atr(mock_df)) is False


def test_validate_trend_angle_buy_pass(execution_filter, mock_df):
    assert bool(execution_filter._validate_trend_angle(mock_df, 1)) is True


def test_validate_trend_angle_buy_fail(execution_filter, mock_df):
    mock_df["M5_ema_50"] = np.linspace(105, 100, 50)
    assert bool(execution_filter._validate_trend_angle(mock_df, 1)) is False


def test_validate_ema_sequence_buy_pass(execution_filter, mock_df):
    # default mock_df: 20(107) > 50(105) > 200(95)
    assert bool(execution_filter._validate_ema_sequence(mock_df, 1)) is True


def test_validate_ema_sequence_buy_fail(execution_filter, mock_df):
    # 20 < 50
    mock_df["M5_ema_20"] = 100.0
    mock_df["M5_ema_50"] = 105.0
    assert bool(execution_filter._validate_ema_sequence(mock_df, 1)) is False


def test_validate_momentum_buy_pass(execution_filter, mock_df):
    assert bool(execution_filter._validate_momentum(mock_df, 1)) is True


def test_validate_momentum_buy_fail(execution_filter, mock_df):
    mock_df["M5_rsi_14"] = 40.0
    assert bool(execution_filter._validate_momentum(mock_df, 1)) is False


def test_validate_drawdown_pass(execution_filter):
    assert execution_filter._validate_drawdown(0.10) is True


def test_validate_drawdown_fail(execution_filter):
    assert execution_filter._validate_drawdown(0.16) is False


@patch("src.trading.execution_filter.datetime")
def test_validate_session_pass(mock_dt, execution_filter):
    # 12:00 UTC
    mock_dt.now.return_value.time.return_value = time(12, 0)
    assert execution_filter._validate_session() is True


@patch("src.trading.execution_filter.datetime")
def test_validate_session_fail(mock_dt, execution_filter):
    # 02:00 UTC
    mock_dt.now.return_value.time.return_value = time(2, 0)
    assert execution_filter._validate_session() is False


@patch("src.trading.execution_filter.ExecutionFilter._validate_session")
def test_full_cascade_buy_approved(mock_session, execution_filter, mock_df, buy_signal):
    mock_session.return_value = True
    decision = execution_filter.validate(buy_signal, mock_df, 0.05)
    assert decision.is_approved is True
    assert decision.blocked_by is None


@patch("src.trading.execution_filter.ExecutionFilter._validate_session")
def test_full_cascade_rejected(mock_session, execution_filter, mock_df, buy_signal):
    mock_session.return_value = True
    mock_df.loc[49, "M5_rsi_14"] = 30.0  # Fails momentum
    decision = execution_filter.validate(buy_signal, mock_df, 0.05)
    assert decision.is_approved is False
    assert decision.blocked_by == "MOMENTUM"
