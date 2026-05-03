"""
MT5 AI/ML Trading Bot - Comprehensive Integration Test Suite
tests/verify_integration.py
Verifies multi-agent work composes into a functioning, reliable system.
"""

import time
import pytest
import numpy as np
import pandas as pd
import torch
import os
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime, timezone
from pydantic import ValidationError

from src.core.config import TradingConfig, get_config
from src.core.monitor import Monitor
from src.core.trade_logger import TradeLogger, RiskEvent
from src.trading.mt5_connector import MT5Connector
from src.trading.risk_manager import RiskManager, TradeSignal
from src.trading.execution_filter import ExecutionFilter, ExecutionDecision
from src.models.ensemble import EnsembleModel
from src.models.regime_detector import RegimeDetector
from src.trading.capital_allocator import CapitalAllocator, StrategyConfig
from src.research.hyperopt_walkforward import WalkForwardOptimizer, WalkForwardConfig
from src.research.benchmarks import EMACrossoverStrategy

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


@pytest.fixture
def sample_market_data():
    dates = pd.date_range(end=datetime.now(timezone.utc), periods=200, freq="5min")
    df = pd.DataFrame(
        {
            "open": np.linspace(2300, 2310, 200),
            "high": np.linspace(2305, 2315, 200),
            "low": np.linspace(2295, 2305, 200),
            "close": np.linspace(2300, 2310, 200),
            "tick_volume": np.random.randint(100, 1000, 200),
        },
        index=dates,
    )

    # Add indicator columns for ExecutionFilter
    df["base_M5_atr"] = 10.0
    df["base_M5_rsi"] = 60.0
    for p in [8, 21, 50, 200]:
        df[f"base_M5_ema_{p}"] = df["close"].ewm(span=p, adjust=False).mean()

    return df


# --- Path 1: Full Trading Flow Integration ---


def test_full_pipeline_integration(
    mock_cfg, trade_logger, mock_monitor, mock_connector, sample_market_data
):
    # Set a Tuesday 10:00 AM UTC to pass session filter
    ts = datetime(2026, 5, 5, 10, 0, 0, tzinfo=timezone.utc)
    """Path 1: Data ingestion -> feature engineering -> model inference -> execution filter -> risk engine -> logging"""
    risk = RiskManager(
        mock_cfg, account_balance=10000.0, logger_db=trade_logger, monitor=mock_monitor
    )
    model = EnsembleModel(device="cpu")
    exec_filter = ExecutionFilter(max_drawdown=0.15)

    # 1. Mock Ingestion
    mock_tick = {"bid": 2310.0, "ask": 2311.0, "time": time.time()}

    with (
        patch.object(mock_connector, "get_ohlcv", return_value=sample_market_data),
        patch.object(mock_connector, "get_tick", return_value=mock_tick),
        patch.object(mock_connector, "place_order", return_value=999888),
    ):
        # 2. Model Inference
        obs = sample_market_data[["open", "high", "low", "close", "tick_volume"]].values[-1]
        model._ppo_model = MagicMock()
        model._ppo_model.predict.return_value = (1, None)  # BUY
        signal_out = model.predict(obs)

        # 3. Log Signal
        signal_id = trade_logger.log_signal(
            {
                "symbol": "XAUUSD",
                "direction": signal_out.direction,
                "entry_price": 2311.0,
                "algorithm": "ensemble",
                "confidence": signal_out.confidence,
            }
        )

        # 4. Risk Engine
        signal = TradeSignal(
            symbol="XAUUSD",
            direction=signal_out.direction,
            entry_price=2311.0,
            stop_loss=2300.0,
            take_profit=2350.0,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=signal_out.confidence,
        )

        risk_approved = risk.approve(signal, signal_id=signal_id)
        assert risk_approved is True

        # 5. Execution Filter
        exec_decision = exec_filter.validate(
            signal, sample_market_data, current_drawdown=0.0, timestamp=ts
        )
        assert exec_decision.is_approved is True

        # 6. Execution & Final Logging
        ticket = mock_connector.place_order(signal)
        assert ticket == 999888

        trade_id = trade_logger.log_trade(
            ticket=ticket,
            symbol="XAUUSD",
            direction=1,
            entry_price=2311.0,
            lot_size=0.1,
            signal_id=signal_id,
        )

        # Data Consistency Check
        trade = trade_logger.get_trade_by_ticket(999888)
        assert trade is not None
        assert trade.signal_id == signal_id


# --- Path 2: Configuration & Startup ---


def test_startup_integration():
    """Path 2: Configuration loading -> validation -> trading mode selection -> monitoring startup"""
    with patch.dict(
        os.environ,
        {
            "MT5_LOGIN": "123456",
            "MT5_PASSWORD": "StartupTestPassword",
            "MT5_SERVER": "StartupTestServer",
            "DATABASE_URL": "sqlite:///trades.db",
            "MODE": "demo",
            "ALGORITHM": "ensemble",
        },
    ):
        get_config.cache_clear()
        cfg = get_config()
        assert cfg.mode == "demo"

        from src.core.config_validator import ConfigValidator

        validator = ConfigValidator(cfg)
        result = validator.validate()
        assert result.success is True


# --- Path 3: Backtesting & Walk-Forward ---


def test_backtest_wf_integration(sample_market_data):
    """Path 3: Backtest initialization -> walk-forward validation -> performance reporting"""

    def param_space(trial):
        return {
            "fast_window": trial.suggest_int("fast_window", 5, 10),
            "slow_window": trial.suggest_int("slow_window", 20, 30),
        }

    config = WalkForwardConfig(
        n_trials=2, train_size=100, test_size=20, step_size=40, min_windows=2
    )
    optimizer = WalkForwardOptimizer(
        data=sample_market_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=param_space,
        config=config,
    )

    result = optimizer.run_optimization()
    assert result.best_params is not None
    assert result.metrics.oos_sharpe_mean is not None


# --- Path 4: Resilience & Error Injection ---


def test_circuit_breaker_recovery(mock_cfg, trade_logger, mock_monitor):
    """Path 4: Error injection -> circuit breaker activation -> recovery -> alert notification"""
    risk = RiskManager(
        mock_cfg, account_balance=10000.0, logger_db=trade_logger, monitor=mock_monitor
    )

    # 1. Trigger Circuit Breaker
    risk.update_equity(10000.0)  # peak
    risk.update_equity(8000.0)  # 20% drawdown (Limit 15%)

    with patch.object(mock_monitor, "alert_circuit_breaker") as mock_alert:
        signal = TradeSignal("XAUUSD", 1, 2300, 2200, 2500, 0.1, "test", 0.9)
        approved = risk.approve(signal)
        assert approved is False
        mock_alert.assert_called_once()

    # 2. Verify Logging
    with trade_logger.Session() as session:
        event = session.query(RiskEvent).filter(RiskEvent.event_type == "CIRCUIT_BREAKER").first()
        assert event is not None

    # 3. Recovery (Simulated by resetting stats)
    risk.peak_equity = 8000.0
    risk.update_equity(8000.0)
    assert risk._check_circuit_breaker() is True


# --- Path 5: Intelligence & Adaptive Weighting ---


def test_ensemble_intelligence_integration(sample_market_data):
    """Path 5: Model ensemble -> regime detection -> dynamic weighting -> trade decision"""
    # 1. Regime Detection
    detector = RegimeDetector()
    regime_info = detector.detect(sample_market_data)
    assert regime_info is not None

    # 2. Ensemble & Dynamic Weighting
    model = EnsembleModel(device="cpu")
    initial_weights = model.weights.copy()

    # Simulate some performance to trigger rebalance
    for _ in range(60):
        model.record_return("ppo", 0.02)
        model.record_return("lstm", -0.01)

    assert model.weights["ppo"] > initial_weights["ppo"]

    # 3. Decision
    model._ppo_model = MagicMock()
    model._ppo_model.predict.return_value = (1, None)
    signal = model.predict(sample_market_data.iloc[-1].values, regime_info=regime_info)
    assert signal.direction == 1


# --- Performance Measurement ---


def test_system_latency_metrics(mock_cfg, trade_logger, sample_market_data):
    """Measures latency of core integration paths."""
    model = EnsembleModel(device="cpu")
    exec_filter = ExecutionFilter()
    obs = sample_market_data.iloc[-1].values

    latencies = []
    for _ in range(50):
        start = time.perf_counter()

        # Full stack logic
        signal_obj = model.predict(obs)
        # Mocking signal for filter
        signal = TradeSignal("XAUUSD", 1, 2300, 2200, 2500, 0.1, "test", 0.8)
        exec_filter.validate(signal, sample_market_data, 0.0)

        latencies.append((time.perf_counter() - start) * 1000)

    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    p99 = np.percentile(latencies, 99)

    print(f"\nLatency Report (ms): P50={p50:.2f}, P95={p95:.2f}, P99={p99:.2f}")
    assert p50 < 200  # Threshold for enterprise responsiveness
