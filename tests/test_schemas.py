import pytest
from pydantic import ValidationError
from datetime import datetime, timezone
from src.schemas.trading import (
    ModelSignalSchema,
    TradeSignalSchema,
    TradeExecutionSchema,
)
from src.schemas.market import OHLCVData
from src.schemas.performance import PerformanceMetricsSchema
from src.schemas.risk import RiskParameters, ExecutionDecision

def test_trade_signal_schema_valid():
    data = {
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0,
        "stop_loss": 1980.0,
        "take_profit": 2040.0,
        "lot_size": 0.1,
        "algorithm": "ensemble",
        "confidence": 0.75,
        "timestamp": datetime.now(timezone.utc),
    }
    signal = TradeSignalSchema(**data)
    assert signal.symbol == "XAUUSD"
    assert signal.direction == 1

def test_trade_signal_schema_invalid_direction():
    data = {
        "symbol": "XAUUSD",
        "direction": 5, # Invalid direction
        "entry_price": 2000.0,
        "stop_loss": 1980.0,
        "take_profit": 2040.0,
        "lot_size": 0.1,
        "algorithm": "ensemble",
        "confidence": 0.75
    }
    with pytest.raises(ValidationError):
        TradeSignalSchema(**data)

def test_trade_signal_schema_invalid_price():
    data = {
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": -100.0, # Invalid price
        "stop_loss": 1980.0,
        "take_profit": 2040.0,
        "lot_size": 0.1,
        "algorithm": "ensemble",
        "confidence": 0.75
    }
    with pytest.raises(ValidationError):
        TradeSignalSchema(**data)

def test_ohlcv_data_valid():
    data = {
        "time": datetime.now(timezone.utc),
        "open": 2000.0,
        "high": 2010.0,
        "low": 1990.0,
        "close": 2005.0,
        "tick_volume": 100,
    }
    ohlcv = OHLCVData(**data)
    assert ohlcv.open == 2000.0


def test_model_signal_schema_hold():
    data = {
        "symbol": "XAUUSD",
        "direction": 0,
        "entry_price": 2000.0,
        "algorithm": "ensemble",
        "confidence": 0.5,
    }
    signal = ModelSignalSchema(**data)
    assert signal.direction == 0

def test_performance_metrics_schema_defaults():
    metrics = PerformanceMetricsSchema()
    assert metrics.sharpe_ratio == 0.0
    assert metrics.total_trades == 0

def test_risk_parameters_invalid_range():
    with pytest.raises(ValidationError):
        RiskParameters(risk_per_trade=0.1) # Max is 0.05
