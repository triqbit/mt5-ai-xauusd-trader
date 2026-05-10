
import pytest
from unittest.mock import MagicMock
from src.trading.risk_manager import RiskManager
from src.core.config import TradingConfig

@pytest.fixture
def risk_manager():
    cfg = MagicMock(spec=TradingConfig)
    cfg.risk_per_trade = 0.01
    cfg.model_drift_threshold = 0.3
    cfg.max_losing_streak = 3
    rm = RiskManager(cfg, account_balance=10000.0)
    return rm

def test_size_position_normal_health(risk_manager):
    # Baseline size with 0.58 win rate and 2.0 R:R (avg_win=2, avg_loss=1)
    # Kelly = (0.58 * 2 - 0.42 * 1) / 2 = (1.16 - 0.42) / 2 = 0.37 -> capped at 0.25
    # Risk capital = 10000 * 0.01 = 100
    # Lot size = (100 * 0.25) / (1 * 1) = 25 lots (ignoring pip value logic for now)

    size = risk_manager.size_position(
        symbol="XAUUSD",
        win_rate=0.58,
        avg_win=2.0,
        avg_loss=1.0,
        model_health={"accuracy": 0.58, "drift": 0.0}
    )
    assert size > 0

    # Size without health data should be same as normal health
    size_no_health = risk_manager.size_position(
        symbol="XAUUSD",
        win_rate=0.58,
        avg_win=2.0,
        avg_loss=1.0,
        model_health=None
    )
    assert size == size_no_health

def test_size_position_low_accuracy_throttle(risk_manager):
    # Normal size
    normal_size = risk_manager.size_position(
        symbol="XAUUSD",
        win_rate=0.58,
        avg_win=2.0,
        avg_loss=1.0,
        model_health={"accuracy": 0.58, "drift": 0.0}
    )

    # Size with accuracy < 0.45 should be significantly reduced
    size_low_acc = risk_manager.size_position(
        symbol="XAUUSD",
        win_rate=0.58,
        avg_win=2.0,
        avg_loss=1.0,
        model_health={"accuracy": 0.40, "drift": 0.0}
    )

    assert size_low_acc < normal_size

def test_drift_multiplier_scaling(risk_manager):
    # Drift trigger is 0.15, drift limit is 0.30.
    # At drift 0.30, penalty should be 20% (multiplier 0.8).

    size_no_drift = risk_manager.size_position(
        symbol="XAUUSD",
        win_rate=0.60,
        avg_win=2.0,
        avg_loss=1.0,
        model_health={"accuracy": 0.60, "drift": 0.0}
    )

    size_max_drift = risk_manager.size_position(
        symbol="XAUUSD",
        win_rate=0.60,
        avg_win=2.0,
        avg_loss=1.0,
        model_health={"accuracy": 0.60, "drift": 0.30}
    )

    # size_max_drift should be exactly 80% of size_no_drift.
    assert size_max_drift == pytest.approx(size_no_drift * 0.8, rel=0.05)

def test_accuracy_win_rate_override(risk_manager):
    # Verify that win_rate passed to size_position is overridden by health['accuracy']
    size_manual = risk_manager.size_position(
        symbol="XAUUSD",
        win_rate=0.70,
        avg_win=2.0,
        avg_loss=1.0,
        model_health=None
    )

    size_override = risk_manager.size_position(
        symbol="XAUUSD",
        win_rate=0.50, # Lower manual win rate
        avg_win=2.0,
        avg_loss=1.0,
        model_health={"accuracy": 0.70, "drift": 0.0} # Higher health accuracy
    )

    assert size_manual == size_override
