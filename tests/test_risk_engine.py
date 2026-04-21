"""Tests for RiskEngine."""
import pytest
from unittest.mock import MagicMock
from src.trading.risk_engine import RiskEngine
from src.trading.risk_manager import TradeSignal
from src.core.config import TradingConfig

@pytest.fixture
def mock_config():
    cfg = MagicMock(spec=TradingConfig)
    cfg.risk_per_trade = 0.01
    cfg.max_position_size_pct = 0.10
    cfg.min_lot_size = 0.01
    cfg.max_leverage = 10.0
    cfg.max_positions = 5
    cfg.max_single_direction_exposure_pct = 0.30
    cfg.margin_halt_level = 0.80
    cfg.confidence_threshold = 0.55
    cfg.daily_loss_limit_level4 = 0.05
    cfg.daily_loss_hard_stop = 0.06
    cfg.max_daily_trades = 20
    cfg.max_losing_streak = 3
    cfg.drawdown_limit_level1 = 0.10
    cfg.drawdown_limit_level2 = 0.15
    cfg.drawdown_limit_level3 = 0.20
    cfg.drawdown_limit_level4 = 0.25
    cfg.drawdown_limit_level5 = 0.30
    cfg.max_weekly_loss = 0.10
    cfg.max_monthly_loss = 0.15
    return cfg

def test_risk_engine_init(mock_config):
    engine = RiskEngine(mock_config, 10000.0)
    assert engine.balance == 10000.0
    assert engine.peak_equity == 10000.0

def test_approve_success(mock_config):
    engine = RiskEngine(mock_config, 10000.0)
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.01,
        algorithm="ppo",
        confidence=0.7
    )
    assert engine.approve(signal) is True

def test_reject_exposure(mock_config):
    engine = RiskEngine(mock_config, 10000.0)
    # Price 2300, Lot 0.2. Notional = 0.2 * 100 * 2300 = 46000.
    # 46000 / 10000 = 460% exposure. Limit is 30%.
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.2,
        algorithm="ppo",
        confidence=0.7
    )
    assert engine.approve(signal) is False

def test_size_position_risk_limited(mock_config):
    mock_config.max_position_size_pct = 0.30 # Allow larger notional
    engine = RiskEngine(mock_config, 1000000.0)
    # Risk 1% of 1,000,000 = 10,000
    # ATR = 50. Stop loss = 2*ATR = 100.
    # Contract = 100.
    # lot_size = 10,000 / (100 * 100) = 1.0
    lot = engine.size_position("XAUUSD", 2300.0, 50.0, 1000000.0)
    assert lot == 1.0
