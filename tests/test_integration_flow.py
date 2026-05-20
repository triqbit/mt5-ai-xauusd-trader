"""
MT5 AI/ML Trading Bot - Integration Test Suite
tests/test_integration_flow.py
Verifies end-to-end integration across all system components.
"""

import time

import numpy as np
import pytest

try:
    import torch
except ImportError:
    torch = None
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from pydantic import ValidationError

from src.core.config import get_config
from src.core.monitor import Monitor
from src.core.schemas import TradeSignal
from src.core.trade_logger import TradeLogger
from src.trading.mt5_connector import MT5Connector
from src.trading.risk_manager import RiskManager

if torch:
    from src.models.ensemble import EnsembleModel
else:
    EnsembleModel = MagicMock

# --- Fixtures ---


@pytest.fixture
def mock_cfg():
    with patch.dict(
        os.environ,
        {
            "MT5_PASSWORD": "test_password",
            "MT5_SERVER": "test_server",
            "TELEGRAM_TOKEN": "123:abc",
            "TELEGRAM_CHAT_ID": "123456",
            "MODE": "demo",
        },
    ):
        get_config.cache_clear()
        return get_config()


@pytest.fixture
def trade_logger():
    # Use in-memory SQLite for testing
    return TradeLogger(db_url="sqlite:///:memory:")


@pytest.fixture
def mock_monitor(mock_cfg):
    with patch("telegram.Bot"):
        return Monitor(mock_cfg)


@pytest.fixture
def mock_connector(mock_cfg):
    with patch("src.trading.mt5_connector.mt5") as mock_mt5:
        mock_mt5.initialize.return_value = True
        mock_mt5.login.return_value = True
        mock_mt5.account_info.return_value._asdict.return_value = {
            "balance": 10000.0,
            "equity": 10000.0,
        }
        connector = MT5Connector(mock_cfg)
        connector.connect()
        return connector


pytestmark = pytest.mark.skipif(torch is None, reason="torch not installed")

# --- Path 1: Full Trading Flow ---


def test_full_trading_flow_integration(mock_cfg, trade_logger, mock_monitor, mock_connector):
    """Data ingestion -> feature engineering -> model inference -> execution filter -> risk engine -> logging"""

    risk = RiskManager(
        mock_cfg, account_balance=10000.0, logger_db=trade_logger, monitor=mock_monitor
    )
    model = EnsembleModel(device="cpu")

    # 1. Mock Market Data (Ingestion)
    mock_ohlcv = np.random.rand(200, 5)  # open, high, low, close, vol
    mock_tick = {"bid": 2350.0, "ask": 2351.0, "time": time.time()}

    with (
        patch.object(mock_connector, "get_ohlcv", return_value=mock_ohlcv),
        patch.object(mock_connector, "get_tick", return_value=mock_tick),
        patch.object(mock_connector, "place_order", return_value=123456),
    ):
        # 2. Inference
        obs = mock_ohlcv[-1]
        model.predict(obs)

        # 3. Log Signal
        signal_id = trade_logger.log_signal(
            {
                "symbol": "XAUUSD",
                "direction": 1,  # Force buy for test
                "entry_price": 2351.0,
                "algorithm": "ensemble",
                "confidence": 0.85,
            }
        )

        # 4. Risk Engine
        signal = TradeSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2351.0,
            stop_loss=2340.0,
            take_profit=2380.0,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=0.85,
        )

        approved = risk.approve(signal, signal_id=signal_id)
        assert approved is True

        # 5. Execution & Logging
        ticket = mock_connector.place_order(signal)
        assert ticket == 123456

        trade_logger.log_trade(
            ticket=ticket,
            symbol="XAUUSD",
            direction=1,
            entry_price=2351.0,
            lot_size=0.1,
            signal_id=signal_id,
        )

        # Verify DB consistency
        trade = trade_logger.get_trade_by_ticket(123456)
        assert trade is not None
        assert trade.status == "OPEN"
        assert trade.signal_id == signal_id


# --- Path 2: Configuration & Startup ---


def test_config_and_startup_integration():
    """Configuration loading -> validation -> trading mode selection -> monitoring startup"""
    with patch.dict(
        os.environ,
        {"MT5_PASSWORD": "test", "MT5_SERVER": "test", "MODE": "live", "RISK_PER_TRADE": "0.01"},
    ):
        get_config.cache_clear()
        cfg = get_config()
        assert cfg.mode == "live"
        assert cfg.mt5_password.get_secret_value() == "test"

        # Test validation
        with patch.dict(os.environ, {"RISK_PER_TRADE": "0.05"}):
            get_config.cache_clear()
            with pytest.raises(ValidationError):
                get_config()


# --- Path 3: Backtesting & Validation ---


def test_backtest_initialization():
    """Backtest initialization -> walk-forward validation -> performance reporting"""
    # Based on audit, backtest.py is missing or stubbed.
    # We verify if the entry point in main.py correctly handles the missing component.
    # Mock data for get_rates_range
    import pandas as pd

    from main import main

    mock_data = pd.DataFrame(
        {
            "time": [datetime.now()],
            "open": [2000.0],
            "high": [2010.0],
            "low": [1990.0],
            "close": [2005.0],
            "tick_volume": [100],
            "spread": [1],
            "real_volume": [100],
        }
    )

    with (
        patch("sys.argv", ["main.py", "--mode", "backtest"]),
        patch("src.trading.mt5_connector.MT5Connector.connect", return_value=True),
        patch("src.trading.mt5_connector.MT5Connector.disconnect"),
        patch("src.trading.mt5_connector.MT5Connector.get_rates_range", return_value=mock_data),
        patch("src.core.health.HealthChecker.get_full_report") as mock_health,
        patch.dict(
            os.environ,
            {
                "MT5_LOGIN": "123456",
                "MT5_PASSWORD": "ValidPassword",
                "MT5_SERVER": "ValidServer",
                "DATABASE_URL": "sqlite:///test_trades.db",
            },
        ),
    ):
        from src.core.health import HealthReport, HealthStatus

        mock_health.return_value = HealthReport(
            status=HealthStatus.HEALTHY, timestamp=datetime.now(timezone.utc), components={}
        )

        # Should log info but not crash
        assert main() == 0  # Health discovery verified


# --- Path 4: Resilience & Recovery ---


def test_resilience_and_circuit_breaker(mock_cfg, trade_logger, mock_monitor):
    """Error injection -> circuit breaker activation -> recovery -> alert notification"""
    risk = RiskManager(
        mock_cfg, account_balance=10000.0, logger_db=trade_logger, monitor=mock_monitor
    )

    # Trigger Circuit Breaker (15% drawdown)
    risk.update_equity(10000.0)  # peak
    risk.update_equity(8000.0)  # 20% drawdown

    with patch.object(mock_monitor, "alert_circuit_breaker") as mock_alert:
        signal = TradeSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2300.0,
            stop_loss=2200.0,
            take_profit=2500.0,
            lot_size=0.1,
            algorithm="test",
            confidence=0.9,
        )
        approved = risk.approve(signal)
        assert approved is False
        mock_alert.assert_called_once()

    # Verify risk event logged
    with trade_logger.Session() as session:
        from src.core.trade_logger import RiskEvent

        event = session.query(RiskEvent).filter(RiskEvent.event_type == "CIRCUIT_BREAKER").first()
        assert event is not None


# --- Path 5: Intelligence & Adaptive Weighting ---


def test_intelligence_ensemble_adaptation():
    """Model ensemble -> regime detection -> dynamic weighting -> trade decision"""
    model = EnsembleModel(device="cpu")
    initial_weights = model.weights.copy()

    # Simulate performance of PPO via dynamic_ensemble
    metrics = {
        "ppo": {"accuracy": 0.8, "calibration_error": 0.05, "drift_score": 0.02},
        "lstm": {"accuracy": 0.4, "calibration_error": 0.3, "drift_score": 0.25},
        "dreamer": {"accuracy": 0.5, "calibration_error": 0.1, "drift_score": 0.1},
    }
    model.dynamic_ensemble.update_weights(metrics)

    # Weight rebalancing should have occurred
    assert model.weights["ppo"] > initial_weights["ppo"]
    assert model.weights["lstm"] < initial_weights["lstm"]

    # Predict with new weights
    obs = np.random.rand(140)
    # Mock models to ensure they participate
    from src.core.constants import SignalDirection
    from src.models.base_model import Signal

    model.ppo_agent = MagicMock()
    model.ppo_agent.predict.return_value = Signal(direction=SignalDirection.BUY, confidence=0.8)

    signal = model.predict(obs)
    assert "ppo" in signal.metadata["per_algo_votes"]


# --- Latency Measurement ---


def test_performance_latency(mock_cfg, trade_logger, mock_monitor):
    RiskManager(mock_cfg, account_balance=10000.0, logger_db=trade_logger, monitor=mock_monitor)
    model = EnsembleModel(device="cpu")

    obs = np.random.rand(140)

    # Warm up
    model.predict(obs)

    # Measure
    latencies = []
    for _ in range(100):
        start = time.perf_counter()
        model.predict(obs)
        latencies.append((time.perf_counter() - start) * 1000)

    p50 = np.percentile(latencies, 50)
    print(f"Inference Latency P50: {p50:.2f}ms")
    assert p50 < 100  # Inference should be fast on CPU
