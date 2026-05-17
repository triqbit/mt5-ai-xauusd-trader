import pytest

try:
    import torch
except ImportError:
    torch = None

pytestmark = pytest.mark.skipif(torch is None, reason="torch not installed")

from unittest.mock import patch

import numpy as np
import pandas as pd

from src.core.schemas import TradeSignal
from src.core.trade_logger import TradeLogger
from src.models.regime_detector import MarketRegime, RegimeDetector
from src.trading.capital_allocator import CapitalAllocator, StrategyConfig
from src.trading.risk_manager import RiskManager


@pytest.fixture
def mock_ohlcv_data():
    """Generate 200 bars of synthetic OHLCV data."""
    dates = pd.date_range(end=pd.Timestamp.now(), periods=200, freq="5min")
    df = pd.DataFrame(
        {
            "open": np.random.uniform(2300, 2350, 200),
            "high": np.random.uniform(2350, 2360, 200),
            "low": np.random.uniform(2290, 2300, 200),
            "close": np.random.uniform(2300, 2350, 200),
            "tick_volume": np.random.randint(100, 1000, 200),
        },
        index=dates,
    )
    return df


def test_institutional_intelligence_path(mock_ohlcv_data):
    """
    Path 1: Market Intelligence Integration
    Verifies that Regime Detection correctly informs the decision cockpit.
    """
    detector = RegimeDetector()
    regime = detector.detect(mock_ohlcv_data)

    assert isinstance(regime.label, MarketRegime)
    assert 0.0 <= regime.confidence <= 1.0


def test_capital_and_risk_integration(tmp_path):
    """
    Path 2: Risk & Capital Allocation
    Verifies that CapitalAllocator correctly throttles risk based on account performance.
    """
    db_file = tmp_path / "test_trades.db"
    trade_logger = TradeLogger(db_url=f"sqlite:///{db_file}")

    with patch("src.core.config.get_config") as mock_get_cfg:
        from src.core.config import TradingConfig

        cfg = TradingConfig(
            mt5_password="fake",
            mt5_server="fake",
            symbol="XAUUSD",
            risk_per_trade=0.01,
            max_drawdown=0.15,
        )
        mock_get_cfg.return_value = cfg

        # 1. Setup Allocator
        allocator = CapitalAllocator(total_budget=100000.0)
        allocator.add_strategy(
            StrategyConfig(
                strategy_id="ENSEMBLE_XAUUSD_M5",
                symbol="XAUUSD",
                model_family="ensemble",
                capital_cap=50000.0,
            )
        )

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
        df_raw = pd.DataFrame({"close": [2350], "atr": [0.1]})
        approved = risk.validate_signal(signal, df_raw, [])
        assert approved.is_approved is True

        # Test rejection (high drawdown simulation)
        risk.update_equity(80000.0)  # 20% drawdown
        approved_after_crash = risk.validate_signal(signal, df_raw, [])
        assert approved_after_crash.is_approved is False
