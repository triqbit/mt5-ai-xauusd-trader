"""
Tests for hardened risk logic and new synthetic scenarios.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import os

from src.core.config import get_config
from src.trading.risk_manager import RiskManager, TradeSignal
from src.utils.synthetic_data import ScenarioGenerator, RiskScenarioBuilder

@pytest.fixture
def mock_cfg():
    with patch.dict(os.environ, {
        "MT5_PASSWORD": "test",
        "MT5_SERVER": "test",
        "CONSECUTIVE_LOSS_LIMIT": "3"
    }):
        get_config.cache_clear()
        return get_config()

@pytest.fixture
def risk_manager(mock_cfg):
    return RiskManager(mock_cfg, account_balance=10000.0)

def test_consecutive_loss_halt(risk_manager):
    """Verify that trading is halted after reaching the consecutive loss limit."""
    # Streak: 1 loss
    risk_manager.record_pnl(-100.0)
    assert risk_manager.daily.consecutive_losses == 1

    signal = TradeSignal(
        symbol="XAUUSD", direction=1, entry_price=2300.0, stop_loss=2290.0,
        take_profit=2350.0, lot_size=0.1, algorithm="test", confidence=0.9,
        market_regime="trending"
    )
    assert risk_manager.approve(signal) is True

    # Streak: 2 losses
    risk_manager.record_pnl(-50.0)
    assert risk_manager.daily.consecutive_losses == 2
    assert risk_manager.approve(signal) is True

    # Streak: 3 losses (Limit hit)
    risk_manager.record_pnl(-20.0)
    assert risk_manager.daily.consecutive_losses == 3
    assert risk_manager.approve(signal) is False # Rejection!

    # Reset streak with a win
    risk_manager.record_pnl(100.0)
    assert risk_manager.daily.consecutive_losses == 0
    assert risk_manager.approve(signal) is True

def test_regime_safety_filter(risk_manager):
    """Verify that unsafe market regimes are blocked."""
    signal = TradeSignal(
        symbol="XAUUSD", direction=1, entry_price=2300.0, stop_loss=2290.0,
        take_profit=2350.0, lot_size=0.1, algorithm="test", confidence=0.9,
        market_regime="trending"
    )
    assert risk_manager.approve(signal) is True

    signal.market_regime = "news_shock"
    assert risk_manager.approve(signal) is False

    signal.market_regime = "unknown"
    assert risk_manager.approve(signal) is False

def test_ensemble_consensus_majority(risk_manager):
    """Verify majority agreement requirement."""
    signal = TradeSignal(
        symbol="XAUUSD", direction=1, entry_price=2300.0, stop_loss=2290.0,
        take_profit=2350.0, lot_size=0.1, algorithm="ensemble", confidence=0.9,
        per_algo_votes={"ppo": 1, "lstm": 1, "dreamer": 0}, # 2/3 agreement = 0.66
        market_regime="trending"
    )
    assert risk_manager.approve(signal) is True

    signal.per_algo_votes = {"ppo": 1, "lstm": 0, "dreamer": 0} # 1/3 agreement = 0.33
    assert risk_manager.approve(signal) is False

def test_ensemble_consensus_strong_dissent(risk_manager):
    """Verify that strong dissent (opposite direction) blocks the trade."""
    signal = TradeSignal(
        symbol="XAUUSD", direction=1, entry_price=2300.0, stop_loss=2290.0,
        take_profit=2350.0, lot_size=0.1, algorithm="ensemble", confidence=0.9,
        per_algo_votes={"ppo": 1, "lstm": 1, "dreamer": -1}, # Strong dissent!
        market_regime="trending"
    )
    # Even if 2/3 agree, the -1 blocks it
    assert risk_manager.approve(signal) is False

def test_new_synthetic_regimes():
    """Verify whipsaw and stale regimes generate expected structures."""
    gen = ScenarioGenerator(seed=42)

    # Whipsaw
    df_whip = gen.generate(n_steps=100, regime="whipsaw")
    assert len(df_whip) == 100
    # Price should show some volatility
    assert df_whip["close"].std() > 0

    # Stale
    df_stale = gen.generate(n_steps=50, regime="stale")
    assert (df_stale["tick_volume"] == 0).all()
    assert df_stale["close"].nunique() == 1

def test_risk_scenario_builder():
    """Verify builder produces expected test cases."""
    builder = RiskScenarioBuilder()

    streak = builder.generate_loss_streak(3)
    assert len(streak) == 3
    assert all(s.direction == 1 for s in streak)

    dissent = builder.generate_dissent_scenario(direction=-1)
    assert dissent.direction == -1
    assert 1.0 in dissent.per_algo_votes.values() # Strong dissent present
