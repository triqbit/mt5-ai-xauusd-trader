"""
MT5 AI/ML Trading Bot - E2E Scenario Tests
tests/test_e2e_scenarios.py
Validates system behavior under specific market conditions using synthetic data.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from src.core.config import get_config
from src.core.schemas import TradeSignal
from src.core.trade_logger import TradeLogger
from src.trading.risk_manager import RiskManager
from src.utils.synthetic_data import ScenarioGenerator


@pytest.fixture
def mock_cfg():
    with patch.dict(
        os.environ, {"MT5_PASSWORD": "test_password", "MT5_SERVER": "test_server", "MODE": "demo"}
    ):
        get_config.cache_clear()
        return get_config()


@pytest.fixture
def trade_logger():
    logger = TradeLogger(db_url="sqlite:///:memory:")
    from src.core.trade_logger import Base
    Base.metadata.create_all(logger.engine)
    return logger


def test_risk_manager_circuit_breaker_on_volatile_data(mock_cfg, trade_logger):
    """Verify that RiskManager halts trading when synthetic volatile data causes a drawdown."""
    risk = RiskManager(mock_cfg, account_balance=10000.0, logger_db=trade_logger)

    # Simulate a series of equity updates reflecting a crash
    risk.update_equity(10000.0)  # Peak
    risk.update_equity(8400.0)  # 16% drawdown (limit is 15%)

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.9,
    )

    # Should be rejected due to circuit breaker
    assert risk.approve(signal) is False


def test_risk_manager_daily_loss_limit(mock_cfg, trade_logger):
    """Verify daily loss limit rejection using simulated losses."""
    # Max daily loss is 0.05 by default
    risk = RiskManager(mock_cfg, account_balance=10000.0, logger_db=trade_logger)

    # Simulate $600 loss on $10,000 balance (6%)
    risk.record_pnl(-600.0)
    risk.update_equity(9400.0)

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.9,
    )

    assert risk.approve(signal) is False


def test_ensemble_model_with_gapping_data(mock_cfg):
    """Test EnsembleModel behavior when encountering gapping market data."""
    # We need to mock torch and SB3 before importing EnsembleModel
    # to avoid AttributeError in CI environments where these aren't fully loaded.
    with (
        patch.dict(
            "sys.modules",
            {"torch": MagicMock(), "torch.nn": MagicMock(), "stable_baselines3": MagicMock()},
        ),
        patch("src.models.LSTMAttentionModel"),
    ):
        from src.models.ensemble import EnsembleModel

        model = EnsembleModel(device="cpu")

        gen = ScenarioGenerator(seed=123)
        df = gen.generate(n_steps=10, regime="gapping")

        # Simple test to ensure predict can handle the data structure
        for i in range(len(df)):
            obs = df.iloc[i][["open", "high", "low", "close", "tick_volume"]].values
            # Should not crash
            direction, _, _ = model.predict(obs)
            assert direction in [-1, 0, 1]


def test_data_integrity_malformed_scenarios():
    """Verify the ScenarioGenerator malformed output is indeed 'bad' for validation logic tests."""
    gen = ScenarioGenerator(seed=42)
    df = gen.generate(n_steps=50, regime="malformed")

    # Example validation logic that should fail on this data
    def validate_data(data):
        if data.isnull().values.any():
            return False, "NaNs detected"
        if (data["high"] < data["low"]).any():
            return False, "High < Low detected"
        if (data[["open", "high", "low", "close"]] < 0).values.any():
            return False, "Negative prices detected"
        return True, "OK"

    is_valid, reason = validate_data(df)
    assert is_valid is False
    assert reason in ["NaNs detected", "High < Low detected", "Negative prices detected"]
