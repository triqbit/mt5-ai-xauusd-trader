try:
    import torch
except ImportError:
    torch = None
import pytest

pytestmark = pytest.mark.skipif(torch is None, reason="torch not installed")

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from src.core.schemas import TradeSignal
from src.core.trade_logger import TradeLogger
from src.models.ensemble import EnsembleModel
from src.models.regime_detector import MarketRegime, RegimeDetector
from src.trading.capital_allocator import CapitalAllocator, StrategyConfig
from src.trading.risk_manager import RiskManager


@pytest.fixture
def mock_ohlcv_data():
    """Generate 200 bars of synthetic OHLCV data."""
    dates = pd.date_range(end=pd.Timestamp.now(), periods=200, freq="5min")
    data = pd.DataFrame(
        {
            "open": np.random.rand(200) + 2300,
            "high": np.random.rand(200) + 2305,
            "low": np.random.rand(200) + 2295,
            "close": np.random.rand(200) + 2300,
            "tick_volume": np.random.randint(100, 1000, 200),
        },
        index=dates,
    )
    return data


@pytest.fixture
def trade_logger():
    return TradeLogger(db_url="sqlite:///:memory:")


def test_institutional_intelligence_path(mock_ohlcv_data, trade_logger):
    """
    Test: Model ensemble -> regime detection -> dynamic weighting -> trade decision
    Covers work from Jules01, Jules04.
    """
    # 1. Regime Detection (Jules04)
    detector = RegimeDetector(window=20, long_window=50)
    regime_info = detector.detect(mock_ohlcv_data)
    assert regime_info.label in MarketRegime.__members__.values()

    # 2. Dynamic Ensemble weighting adjustment (Jules04)
    ensemble = EnsembleModel(device="cpu")
    initial_weights = ensemble.weights.copy()

    # Simulate performance metrics for models
    metrics = {
        "ppo": {"accuracy": 0.65, "calibration_error": 0.1, "drift_score": 0.05},
        "lstm": {"accuracy": 0.45, "calibration_error": 0.3, "drift_score": 0.2},
        "dreamer": {"accuracy": 0.55, "calibration_error": 0.1, "drift_score": 0.1},
    }

    # Force update via dynamic_ensemble (underlying EnsembleModel's rebalance_weights uses Sharpe)
    ensemble.dynamic_ensemble.update_weights(metrics, regime_info=regime_info)
    new_weights = ensemble.weights

    # PPO should have gained weight due to higher accuracy and lower drift
    assert new_weights["ppo"] > initial_weights["ppo"]
    assert new_weights["lstm"] < initial_weights["lstm"]

    # 3. Model Inference (Jules01)
    # Mock models to simulate votes
    from src.core.constants import SignalDirection
    from src.models.base_model import Signal

    ensemble.ppo_agent = MagicMock()
    # Mock PPO to return action index 1 (BUY in ModelAction/SignalDirection standard)
    ensemble.ppo_agent.predict.return_value = Signal(direction=SignalDirection.BUY, confidence=0.8)

    obs = mock_ohlcv_data.iloc[-1][["open", "high", "low", "close", "tick_volume"]].values
    signal_obj = ensemble.predict(obs)

    assert signal_obj.direction == SignalDirection.BUY
    assert signal_obj.confidence > 0.5


def test_capital_and_risk_integration(trade_logger):
    """
    Test: Capital Allocator -> Risk Manager -> Trade Approval
    Covers work from Jules04, Jules01, Jules02.
    """
    with patch("src.core.config.get_config") as mock_get_cfg:
        cfg = MagicMock()
        cfg.risk_per_trade = 0.02
        cfg.max_daily_loss = 0.05
        cfg.max_positions = 3
        cfg.max_losing_streak = 5
        mock_get_cfg.return_value = cfg

        # 1. Capital Allocation (Jules04)
        allocator = CapitalAllocator(total_budget=100000.0)
        strat_cfg = StrategyConfig(
            strategy_id="ensemble_gold",
            symbol="XAUUSD",
            model_family="ensemble",
            capital_cap=50000.0,
        )
        allocator.add_strategy(strat_cfg)

        allocation = allocator.request_allocation("ensemble_gold", risk_pct=0.01)
        assert allocation.is_allowed is True
        assert allocation.allocated_amount == 1000.0  # 1% of 100k

        # 2. Risk Management Approval (Jules01/Jules02)
        risk = RiskManager(cfg, account_balance=100000.0, logger_db=trade_logger)

        signal = TradeSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2350.0,
            stop_loss=2340.0,
            take_profit=2380.0,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=0.85,
        )

        # Signal approval
        approved = risk.approve(signal)
        assert approved is True

        # Test rejection (high drawdown simulation)
        risk.update_equity(80000.0)  # 20% drawdown
        approved_after_crash = risk.approve(signal)
        assert approved_after_crash is False
