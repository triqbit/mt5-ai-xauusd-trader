import pytest
import time
import numpy as np
import pandas as pd
import torch
import sys
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime, timezone

# Mock MetaTrader5 before importing components that might use it
sys.modules["MetaTrader5"] = MagicMock()

from src.core.config import TradingConfig, get_config
from src.core.monitor import Monitor
from src.core.trade_logger import TradeLogger
from src.models.ensemble import EnsembleModel
from src.trading.mt5_connector import MT5Connector
from src.trading.risk_manager import RiskManager, TradeSignal
from src.environment.gym_env import TradingEnv

# Helper to measure latency
def measure_latency(func, *args, **kwargs):
    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()
    return result, (end - start) * 1000  # ms

class IntegrationMetrics:
    def __init__(self):
        self.latencies = []

    def add(self, latency):
        self.latencies.append(latency)

    def report(self):
        if not self.latencies:
            return "N/A"
        p50 = np.percentile(self.latencies, 50)
        p95 = np.percentile(self.latencies, 95)
        p99 = np.percentile(self.latencies, 99)
        return f"{p50:.2f}/{p95:.2f}/{p99:.2f}"

@pytest.fixture
def mock_cfg():
    with patch.dict("os.environ", {
        "MT5_PASSWORD": "test_password",
        "MT5_SERVER": "test_server",
        "DATABASE_URL": "sqlite:///:memory:"
    }):
        # Clear lru_cache for get_config
        get_config.cache_clear()
        cfg = get_config()
        return cfg

@pytest.fixture
def trade_logger():
    return TradeLogger(db_url="sqlite:///:memory:")

@pytest.fixture
def monitor(mock_cfg):
    with patch("telegram.Bot"):
        return Monitor(mock_cfg)

@pytest.fixture
def risk_manager(mock_cfg, trade_logger, monitor):
    return RiskManager(mock_cfg, account_balance=10000.0, logger_db=trade_logger, monitor=monitor)

@pytest.fixture
def ensemble_model():
    return EnsembleModel(device="cpu")

@pytest.fixture
def connector(mock_cfg):
    with patch("src.trading.mt5_connector.mt5") as mock_mt5:
        mock_mt5.initialize.return_value = True
        conn = MT5Connector(mock_cfg)
        conn.initialize()
        return conn

# 1. Data ingestion → feature engineering → model inference → execution filter → risk engine → logging
def test_path_1_e2e_data_to_logging(mock_cfg, connector, ensemble_model, risk_manager, trade_logger):
    metrics = IntegrationMetrics()

    # Mock market data
    df_mock = pd.DataFrame({
        "open": [2000.0] * 200,
        "high": [2005.0] * 200,
        "low": [1995.0] * 200,
        "close": [2002.0] * 200,
        "tick_volume": [100] * 200
    })
    tick_mock = {"bid": 2001.0, "ask": 2002.0}

    def run_cycle(i):
        with patch.object(connector, 'get_ohlcv', return_value=df_mock), \
             patch.object(connector, 'get_tick', return_value=tick_mock):
            # Data ingestion
            df = connector.get_ohlcv(mock_cfg.symbol, mock_cfg.timeframe, n_bars=200)
            tick = connector.get_tick(mock_cfg.symbol)

            # Feature engineering (simplified)
            obs = df[["open", "high", "low", "close", "tick_volume"]].values[-1]

            # Model inference
            ensemble_model._ppo_model = MagicMock()
            ensemble_model._ppo_model.predict.return_value = (0, {}) # action 0 is BUY

            direction, confidence, _ = ensemble_model.predict(obs)

            # Execution filter & Risk engine
            price = tick["ask"] if direction == 1 else tick["bid"]
            atr = 10.0 # simplified
            signal = TradeSignal(
                symbol=mock_cfg.symbol,
                direction=direction,
                entry_price=price,
                stop_loss=price - direction * 2 * atr,
                take_profit=price + direction * 4 * atr,
                lot_size=0.1,
                algorithm="ppo",
                confidence=confidence
            )

            signal_id = trade_logger.log_signal({
                "symbol": mock_cfg.symbol,
                "direction": direction,
                "entry_price": price,
                "algorithm": "ppo",
                "confidence": confidence
            })

            if risk_manager.approve(signal, signal_id=signal_id):
                ticket = 123456 + i # Unique ticket
                with patch.object(connector, 'place_order', return_value=ticket):
                    res_ticket = connector.place_order(signal)
                    if res_ticket:
                        trade_logger.log_trade(
                            ticket=res_ticket,
                            symbol=mock_cfg.symbol,
                            direction=direction,
                            entry_price=price,
                            lot_size=0.1,
                            signal_id=signal_id
                        )
                        return True
            return False

    # Run multiple times for latency
    for i in range(10):
        _, lat = measure_latency(run_cycle, i)
        metrics.add(lat)

    print(f"\nPath 1 Latency (P50/P95/P99): {metrics.report()} ms")
    from src.core.trade_logger import ModelSignal
    assert len(trade_logger.Session().query(ModelSignal).all()) > 0

# 2. Configuration loading → validation → trading mode selection → monitoring startup
def test_path_2_config_to_monitoring():
    metrics = IntegrationMetrics()

    def run_init():
        with patch.dict("os.environ", {
            "MT5_PASSWORD": "test_password",
            "MT5_SERVER": "test_server",
            "DATABASE_URL": "sqlite:///:memory:"
        }):
            get_config.cache_clear()
            cfg = get_config()
            assert cfg.symbol == "XAUUSD"

            with patch("telegram.Bot"):
                monitor = Monitor(cfg)
                assert monitor is not None

            trade_logger = TradeLogger(db_url="sqlite:///:memory:")
            assert trade_logger is not None

            # Test validation
            with pytest.raises(Exception): # Pydantic ValidationError
                # risk_per_trade > 0.02 should fail
                TradingConfig(mt5_password="p", mt5_server="s", risk_per_trade=0.05)

    for _ in range(10):
        _, lat = measure_latency(run_init)
        metrics.add(lat)

    print(f"\nPath 2 Latency (P50/P95/P99): {metrics.report()} ms")

# 3. Backtest initialization → walk-forward validation → performance reporting
def test_path_3_backtest_to_reporting():
    metrics = IntegrationMetrics()

    def run_backtest_sim(iteration):
        trade_logger = TradeLogger(db_url="sqlite:///:memory:")
        # Simulate backtest using TradingEnv
        data = np.random.randn(1000, 5)
        env = TradingEnv(data)
        obs, _ = env.reset()

        # Simulate some trades
        for i in range(100):
            action = 1 if i % 10 == 0 else (2 if i % 10 == 5 else 0)
            obs, reward, term, trunc, info = env.step(action)

            # Log results as if it were a backtest
            if action != 0:
                ticket = iteration * 1000 + i
                trade_logger.log_trade(
                    ticket=ticket,
                    symbol="XAUUSD",
                    direction=1 if action == 1 else -1,
                    entry_price=100.0,
                    lot_size=0.1,
                    status="CLOSED" if action == 2 else "OPEN"
                )
                if action == 2:
                    # Closing the previous BUY trade
                    trade_logger.update_trade(ticket=iteration * 1000 + i - 5, exit_price=110.0, pnl=10.0)

        # Performance reporting
        report = trade_logger.read_performance_report()
        assert "sharpe_ratio" in report
        return report

    for iteration in range(5):
        _, lat = measure_latency(run_backtest_sim, iteration)
        metrics.add(lat)

    print(f"\nPath 3 Latency (P50/P95/P99): {metrics.report()} ms")

# 4. Error injection → circuit breaker activation → recovery → alert notification
def test_path_4_error_resiliency(risk_manager, monitor, trade_logger):
    metrics = IntegrationMetrics()

    def run_failure_scenario():
        # Reset risk manager state
        risk_manager.balance = 10000.0
        risk_manager.peak_equity = 10000.0

        # Inject huge loss to trigger circuit breaker
        risk_manager.update_equity(5000.0) # 50% drawdown from 10000.0

        signal = TradeSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            stop_loss=1980.0,
            take_profit=2040.0,
            lot_size=0.1,
            algorithm="ppo",
            confidence=0.8
        )

        # Circuit breaker should reject
        approved = risk_manager.approve(signal)
        assert approved is False

        # Recovery
        risk_manager.peak_equity = 5000.0
        risk_manager.update_equity(5000.0)
        approved_after_reset = risk_manager.approve(signal)
        assert approved_after_reset is True

    for _ in range(5):
        _, lat = measure_latency(run_failure_scenario)
        metrics.add(lat)

    print(f"\nPath 4 Latency (P50/P95/P99): {metrics.report()} ms")

# 5. Model ensemble → regime detection → dynamic weighting → trade decision
def test_path_5_ensemble_intelligence(ensemble_model):
    metrics = IntegrationMetrics()

    def run_ensemble_logic():
        obs = np.random.randn(5)

        # Mock models
        ensemble_model._ppo_model = MagicMock()
        ensemble_model._ppo_model.predict.return_value = (0, {}) # BUY

        ensemble_model.lstm_model = MagicMock()
        ensemble_model.lstm_model.side_effect = lambda x: torch.tensor([[10.0, -10.0, -10.0]]) # Strong BUY

        # Test prediction
        direction, confidence, per_algo = ensemble_model.predict(obs, seq=torch.randn(10, 140))
        assert direction == 1

        # Test dynamic weighting
        ensemble_model.record_return("ppo", 0.01)
        # Should trigger rebalance after 50 records, let's force it
        for _ in range(50):
            ensemble_model.record_return("ppo", 0.01)
            ensemble_model.record_return("lstm", -0.01)

        assert ensemble_model.weights["ppo"] > ensemble_model.weights["lstm"]

    for _ in range(5):
        _, lat = measure_latency(run_ensemble_logic)
        metrics.add(lat)

    print(f"\nPath 5 Latency (P50/P95/P99): {metrics.report()} ms")

if __name__ == "__main__":
    pytest.main([__file__])
