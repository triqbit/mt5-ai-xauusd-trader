
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.core.config import TradingConfig
from src.core.schemas import TradeSignal
from src.trading.execution_filter import ExecutionFilter


@pytest.fixture
def mock_config():
    config = MagicMock(spec=TradingConfig)
    config.min_confidence = 0.6
    config.confidence_threshold = 0.6
    config.model_drift_threshold = 0.3
    config.model_accuracy_floor = 0.5
    config.model_win_rate_floor = 0.45
    config.signal_flicker_window = 6
    config.max_signal_changes = 3
    return config

@pytest.fixture
def execution_filter(mock_config):
    return ExecutionFilter(max_drawdown=0.15, config=mock_config)

@pytest.fixture
def valid_signal():
    # Use a fixed Wednesday timestamp to avoid SESSION_CLOSED errors
    return TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.7,
        timestamp=datetime(2024, 5, 22, 12, 0, tzinfo=UTC)
    )

@pytest.fixture
def mock_market_data():
    # Construct a trend-following sequence to satisfy TREND_ANGLE and EMA_SEQUENCE
    # For BUY: prices should be increasing, EMA8 > EMA21 > EMA50 > EMA200
    df = pd.DataFrame({
        "high": [1900.0 + i for i in range(100)],
        "low": [1890.0 + i for i in range(100)],
        "close": [1895.0 + i for i in range(100)],
    })
    # Add EMA columns manually to ensure they pass
    df["base_M5_ema_8"] = df["close"].ewm(span=8).mean()
    df["base_M5_ema_21"] = df["close"].ewm(span=21).mean()
    df["base_M5_ema_50"] = df["close"].ewm(span=50).mean()
    df["base_M5_ema_200"] = df["close"].ewm(span=200).mean()
    df["base_M5_atr"] = 10.0
    df["base_M5_rsi"] = 60.0
    return df

def test_filter_with_high_drift(execution_filter, valid_signal, mock_market_data):
    health = {"drift": 0.4, "accuracy": 0.8}
    decision = execution_filter.validate(valid_signal, mock_market_data, 0.05, model_health=health)
    assert decision.is_approved is False
    assert decision.blocked_by == "MODEL_STABILITY"

def test_filter_with_low_accuracy(execution_filter, valid_signal, mock_market_data):
    health = {"drift": 0.1, "accuracy": 0.4}
    decision = execution_filter.validate(valid_signal, mock_market_data, 0.05, model_health=health)
    assert decision.is_approved is False
    assert decision.blocked_by == "MODEL_STABILITY"

def test_filter_with_healthy_model(execution_filter, valid_signal, mock_market_data):
    health = {"drift": 0.1, "accuracy": 0.7}
    decision = execution_filter.validate(valid_signal, mock_market_data, 0.05, model_health=health)
    # Adjust mock data to ensure earlier layers pass
    assert decision.is_approved is True

def test_filter_with_model_stability_in_trace(execution_filter, valid_signal, mock_market_data):
    health = {"drift": 0.1, "accuracy": 0.7}
    decision = execution_filter.validate(valid_signal, mock_market_data, 0.05, model_health=health)
    assert "model_stability" in decision.trace

def test_filter_low_historical_win_rate(execution_filter, valid_signal, mock_market_data):
    mock_logger = MagicMock()
    mock_logger.read_performance_report.return_value = {"win_rate": 0.4, "total_trades": 25}
    decision = execution_filter.validate(valid_signal, mock_market_data, 0.05, trade_logger=mock_logger)
    assert decision.is_approved is False
    assert decision.blocked_by == "PERFORMANCE_FLOOR"

def test_filter_low_confidence_threshold(execution_filter, valid_signal, mock_market_data):
    execution_filter.cfg.min_confidence = 0.8
    valid_signal = valid_signal.model_copy(update={"confidence": 0.7})
    decision = execution_filter.validate(valid_signal, mock_market_data, 0.05)
    assert decision.is_approved is False
    assert decision.blocked_by == "CONFIDENCE_THRESHOLD"
