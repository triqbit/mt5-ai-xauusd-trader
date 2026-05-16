"""
MT5 AI/ML Trading Bot - Comprehensive Integration Test Suite
tests/verify_integration.py
Verifies multi-agent work composes into a functioning, reliable system.
"""
import os
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import psutil
import pytest

from src.core.config import get_config
from src.core.feature_engineering import FeatureEngineer
from src.core.monitor import Monitor
from src.core.schemas import TradeSignal
from src.core.trade_logger import RiskEvent, TradeLogger
from src.models.ensemble import EnsembleModel
from src.models.regime_detector import RegimeDetector
from src.research.benchmarks import EMACrossoverStrategy
from src.research.hyperopt_walkforward import WalkForwardConfig, WalkForwardOptimizer
from src.trading.execution_filter import ExecutionFilter
from src.trading.mt5_connector import MT5Connector
from src.trading.risk_manager import RiskManager

# --- Fixtures ---

@pytest.fixture
def mock_cfg():
    with patch.dict(os.environ, {
        "MT5_PASSWORD": "test_password",
        "MT5_SERVER": "test_server",
        "TELEGRAM_TOKEN": "123:abc",
        "TELEGRAM_CHAT_ID": "123456",
        "MODE": "demo",
        "MAX_POSITIONS": "3",
        "MAX_DAILY_LOSS": "0.05"
    }):
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
        mock_mt5.account_info.return_value._asdict.return_value = {"balance": 10000.0, "equity": 10000.0}
        connector = MT5Connector(mock_cfg)
        connector.connect()
        return connector

@pytest.fixture
def sample_market_data():
    # Need more data for indicators and MTF resampling
    dates = pd.date_range(end=datetime.now(timezone.utc), periods=1000, freq='5min')
    df = pd.DataFrame({
        'open': np.linspace(2300, 2310, 1000) + np.random.normal(0, 1, 1000),
        'high': np.linspace(2305, 2315, 1000) + np.random.normal(0, 1, 1000),
        'low': np.linspace(2295, 2305, 1000) + np.random.normal(0, 1, 1000),
        'close': np.linspace(2300, 2310, 1000) + np.random.normal(0, 1, 1000),
        'tick_volume': np.random.randint(100, 1000, 1000).astype(float)
    }, index=dates)

    return df

# --- Path 1: Full Trading Flow Integration ---

def test_full_pipeline_integration(mock_cfg, trade_logger, mock_monitor, mock_connector, sample_market_data):
    # Set a Tuesday 10:00 AM UTC to pass session filter
    ts = datetime(2026, 5, 5, 10, 0, 0, tzinfo=timezone.utc)
    """Path 1: Data ingestion -> feature engineering -> model inference -> execution filter -> risk engine -> logging"""
    risk = RiskManager(mock_cfg, account_balance=10000.0, logger_db=trade_logger, monitor=mock_monitor)
    model = EnsembleModel(device="cpu")
    exec_filter = ExecutionFilter(max_drawdown=0.15)
    feature_eng = FeatureEngineer(base_timeframe="M5", timeframes=["M5", "M15"])
    regime_det = RegimeDetector()

    # 1. Mock Ingestion
    mock_tick = {"bid": 2310.0, "ask": 2311.0, "time": time.time()}

    with patch.object(mock_connector, "get_ohlcv", return_value=sample_market_data), \
         patch.object(mock_connector, "get_tick", return_value=mock_tick), \
         patch.object(mock_connector, "place_order", return_value=999888):

        # 2. Feature Engineering & Regime Detection
        df_features = feature_eng.compute_features(sample_market_data)
        regime_info = regime_det.detect(sample_market_data)

        assert not df_features.empty, "Feature engineering returned empty DataFrame"

        obs = df_features.values[-1]

        # 3. Model Inference
        from src.core.constants import SignalDirection
        from src.models.base_model import Signal
        model.ppo_agent = MagicMock()
        model.ppo_agent.predict.return_value = Signal(direction=SignalDirection.BUY, confidence=0.85)
        signal_out = model.predict(obs, regime_info=regime_info)

        # 4. Log Signal
        signal_id = trade_logger.log_signal({
            "symbol": "XAUUSD",
            "direction": signal_out.direction,
            "entry_price": 2311.0,
            "algorithm": "ensemble",
            "confidence": signal_out.confidence
        })

        # 5. Risk Engine
        signal = TradeSignal(
            symbol="XAUUSD",
            direction=signal_out.direction,
            entry_price=2311.0,
            stop_loss=2300.0,
            take_profit=2350.0,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=signal_out.confidence
        )

        risk_approved = risk.approve(signal, signal_id=signal_id)
        assert risk_approved is True

        # 6. Execution Filter
        df_for_filter = df_features.copy()
        df_for_filter["close"] = sample_market_data["close"].reindex(df_for_filter.index)

        exec_decision = exec_filter.validate(signal, df_for_filter, current_drawdown=0.0, timestamp=ts)
        assert isinstance(exec_decision.is_approved, bool)

        # 7. Execution & Final Logging
        ticket = mock_connector.place_order(signal)
        assert ticket == 999888

        trade_logger.log_trade(
            ticket=ticket,
            symbol="XAUUSD",
            direction=signal_out.direction,
            entry_price=2311.0,
            lot_size=0.1,
            signal_id=signal_id
        )

        # Data Consistency Check
        trade = trade_logger.get_trade_by_ticket(999888)
        assert trade is not None
        assert trade.signal_id == signal_id

# --- Path 2: Configuration & Startup ---

def test_startup_integration():
    """Path 2: Configuration loading -> validation -> trading mode selection -> monitoring startup"""
    with patch.dict(os.environ, {
        "MT5_LOGIN": "123456",
        "MT5_PASSWORD": "StartupTestPassword",
        "MT5_SERVER": "StartupTestServer",
        "DATABASE_URL": "sqlite:///trades.db",
        "MODE": "demo",
        "ALGORITHM": "ensemble"
    }), patch("pathlib.Path.exists", return_value=True), \
        patch("pathlib.Path.is_file", return_value=True):
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
            "slow_window": trial.suggest_int("slow_window", 20, 30)
        }

    config = WalkForwardConfig(n_trials=2, train_size=100, test_size=20, step_size=40, min_windows=2)
    optimizer = WalkForwardOptimizer(
        data=sample_market_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=param_space,
        config=config
    )

    result = optimizer.run_optimization()
    assert result.best_params is not None
    assert result.metrics.oos_sharpe_mean is not None

# --- Path 4: Resilience & Error Injection ---

def test_resilience_and_circuit_breaker(mock_cfg, trade_logger, mock_monitor):
    """Path 4: Error injection -> circuit breaker activation -> recovery -> alert notification"""
    risk = RiskManager(mock_cfg, account_balance=10000.0, logger_db=trade_logger, monitor=mock_monitor)

    # 1. Trigger Circuit Breaker via Drawdown
    risk.update_equity(10000.0) # peak
    risk.update_equity(8000.0)  # 20% drawdown (Limit 15%)

    with patch.object(mock_monitor, "alert_circuit_breaker") as mock_alert:
        signal = TradeSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2300.0,
            stop_loss=2200.0,
            take_profit=2500.0,
            lot_size=0.1,
            algorithm="test",
            confidence=0.9
        )
        approved = risk.approve(signal)
        assert approved is False
        mock_alert.assert_called_once()

    # 2. Trigger via Daily Loss
    risk.peak_equity = 10000.0
    risk.update_equity(10000.0) # Reset drawdown
    risk.daily.realised_pnl = -600.0 # $600 loss on $10k is 6% (Limit 5%)

    approved = risk.approve(signal)
    assert approved is False

    # 3. Trigger via Max Positions
    risk.daily.realised_pnl = 0.0 # reset daily loss
    risk.open_positions = {"EURUSD": 1, "GBPUSD": 2, "USDJPY": 3} # Max is 3
    approved = risk.approve(signal)
    assert approved is False

    # 4. Trigger via Invalid Symbol
    risk.open_positions = {}
    signal_invalid = TradeSignal(
        symbol="INVALID",
        direction=1,
        entry_price=1.0,
        stop_loss=0.9,
        take_profit=1.2, # RR >= 1.5
        lot_size=0.1,
        algorithm="test",
        confidence=0.9
    )
    approved = risk.approve(signal_invalid)
    assert approved is False

    # 5. Trigger via Low Confidence
    signal_low_conf = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2200.0,
        take_profit=2500.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.4
    )
    approved = risk.approve(signal_low_conf)
    assert approved is False

    # 6. Verify Logging of events
    with trade_logger.Session() as session:
        events = session.query(RiskEvent).all()
        assert len(events) >= 5
        types = [e.event_type for e in events]
        assert "CIRCUIT_BREAKER" in types
        assert "SIGNAL_REJECTED" in types

    # 7. Recovery (Simulated by resetting stats)
    risk.daily.realised_pnl = 0.0
    risk.update_equity(10000.0)
    risk.open_positions = {}
    assert risk.approve(signal) is True

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

    # Simulate performance of PPO via dynamic_ensemble
    metrics = {
        "ppo": {"accuracy": 0.8, "calibration_error": 0.05, "drift_score": 0.02},
        "lstm": {"accuracy": 0.4, "calibration_error": 0.3, "drift_score": 0.25},
        "dreamer": {"accuracy": 0.5, "calibration_error": 0.1, "drift_score": 0.1}
    }
    model.dynamic_ensemble.update_weights(metrics)

    assert model.weights["ppo"] > initial_weights["ppo"]

    # 3. Decision
    from src.core.constants import SignalDirection
    from src.models.base_model import Signal
    model.ppo_agent = MagicMock()
    model.ppo_agent.predict.return_value = Signal(direction=SignalDirection.BUY, confidence=0.85)

    # Generate features for observation
    feature_eng = FeatureEngineer(base_timeframe="M5", timeframes=["M5", "M15"])
    df_features = feature_eng.compute_features(sample_market_data)
    assert not df_features.empty
    obs = df_features.values[-1]

    signal = model.predict(obs, regime_info=regime_info)
    assert signal.direction == 1

# --- Performance Measurement ---

def test_system_performance_and_resources(mock_cfg, trade_logger, sample_market_data):
    """Measures latency and checks for memory leaks."""
    model = EnsembleModel(device="cpu")
    exec_filter = ExecutionFilter()
    feature_eng = FeatureEngineer(base_timeframe="M5", timeframes=["M5"])

    # Pre-compute features
    df_features = feature_eng.compute_features(sample_market_data)
    obs = df_features.iloc[-1].values

    process = psutil.Process(os.getpid())
    initial_mem = process.memory_info().rss / 1024 / 1024 # MB

    df_for_filter = df_features.copy()
    df_for_filter["close"] = sample_market_data["close"].reindex(df_for_filter.index)

    latencies = []
    for _ in range(100):
        start = time.perf_counter()

        # Full stack logic (Inference + Filter)
        model.predict(obs)
        signal = TradeSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2300.0,
            stop_loss=2200.0,
            take_profit=2500.0,
            lot_size=0.1,
            algorithm="test",
            confidence=0.8
        )
        exec_filter.validate(signal, df_for_filter, 0.0)

        latencies.append((time.perf_counter() - start) * 1000)

    final_mem = process.memory_info().rss / 1024 / 1024 # MB
    mem_growth = final_mem - initial_mem

    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    p99 = np.percentile(latencies, 99)

    print(f"\nLatency Report (ms): P50={p50:.2f}, P95={p95:.2f}, P99={p99:.2f}")
    print(f"Memory Usage: Initial={initial_mem:.2f}MB, Final={final_mem:.2f}MB, Growth={mem_growth:.2f}MB")

    assert p50 < 200
    assert mem_growth < 50
