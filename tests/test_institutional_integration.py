"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_institutional_integration.py

Integration tests covering the end-to-end flow from Research (Jules04)
to Execution (Jules01) and Safety (Jules02), coordinated by Jules05.
"""

import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np

try:
    import torch
except ImportError:
    torch = None

from src.core.schemas import TradeSignal
from src.core.trade_logger import TradeLogger
from src.trading.risk_manager import RiskManager
from src.trading.capital_allocator import CapitalAllocator, StrategyConfig, AllocationRequest
from src.models.regime_detector import RegimeDetector, MarketRegime, RegimeInfo

# Skip all tests in this module if torch is not available
# This allows CI to run base tests without heavy ML dependencies
pytestmark = pytest.mark.skipif(torch is None, reason="torch not installed")

@pytest.fixture
def trade_logger(tmp_path):
    db_path = tmp_path / "test_trades.db"
    return TradeLogger(db_url=f"sqlite:///{db_path}")

def test_institutional_intelligence_path():
    """
    Test: Regime Detection -> Model Contextualization.
    Covers work from Jules04 and Jules01.
    """
    # 1. Regime Detection (Jules04)
    detector = RegimeDetector()
    data = pd.DataFrame({
        "open": np.random.randn(100) + 2300,
        "high": np.random.randn(100) + 2310,
        "low": np.random.randn(100) + 2290,
        "close": np.random.randn(100) + 2300,
        "volume": np.random.randint(100, 1000, 100)
    })

    regime = detector.detect(data)
    assert isinstance(regime, RegimeInfo)
    assert regime.label in [
        MarketRegime.TRENDING,
        MarketRegime.RANGING,
        MarketRegime.VOLATILE_BREAKOUT,
        MarketRegime.NEWS_SHOCK,
        MarketRegime.MEAN_REVERSION,
        MarketRegime.LOW_VOLATILITY_DRIFT,
    ]

    # 2. Model Input Contextualization (Jules01)
    # Ensure model interface accepts regime_info
    from src.models.ensemble import EnsembleModel
    from src.models.base_model import Signal
    model = EnsembleModel(device="cpu")

    obs = np.random.randn(140) # Standard feature set size
    signal = model.predict(obs, regime_info=regime)

    assert isinstance(signal, Signal)
    # Signal (BaseModel output) might not have symbol, metadata might be None if HOLD
    if signal.direction != 0:
        assert "regime" in signal.metadata
        assert signal.metadata["regime"] == regime.label.value

def test_capital_and_risk_integration(trade_logger):
    """
    Test: Capital Allocator -> Risk Manager -> Trade Approval
    Covers work from Jules04, Jules01, Jules02.
    """
    from src.core.config import TradingConfig
    with patch("src.core.config.get_config") as mock_get_cfg:
        cfg = TradingConfig(
            MT5_PASSWORD="test",
            MT5_SERVER="test",
            SYMBOL="XAUUSD",
            RISK_PER_TRADE=0.02,
            MAX_DAILY_LOSS=0.05,
            MAX_POSITIONS=3,
            MAX_LOSING_STREAK=5,
            MAX_DRAWDOWN=0.15,
            MIN_CONFIDENCE=0.55,
            MAX_TRADES_PER_DAY=50,
            MODEL_DRIFT_THRESHOLD=0.1,
            MODEL_ACCURACY_FLOOR=0.5,
            MODEL_CALIBRATION_THRESHOLD=0.2,
            MIN_LOT_SIZE=0.01
        )
        mock_get_cfg.return_value = cfg

        # 1. Capital Allocation (Jules04)
        allocator = CapitalAllocator(total_budget=100000.0)
        strat_cfg = StrategyConfig(
            strategy_id="ensemble_gold",
            symbol="XAUUSD",
            model_family="ensemble",
            capital_cap=50000.0
        )
        allocator.add_strategy(strat_cfg)

        allocation = allocator.request_allocation("ensemble_gold", risk_pct=0.01)
        assert allocation.is_allowed is True
        assert allocation.allocated_amount == 1000.0 # 1% of 100k

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
            confidence=0.85
        )

        # Signal approval
        approved = risk.approve(signal)
        assert approved is True

        # 3. Size position with ATR (Jules01)
        market_data = pd.DataFrame({
            "atr": [5.0] * 20,
            "close": [2350.0] * 20
        })
        lot_size = risk.size_position("XAUUSD", market_data)
        assert lot_size > 0
        assert lot_size <= 2.0 # Sanity cap (10% of 100k at 2350 price)

def test_full_system_coherence(trade_logger):
    """
    Final coherence check: All agents' work must interoperate.
    """
    # Ensure all key modules can be instantiated and linked
    from src.core.decision_support import DecisionSupportSystem
    from src.trading.execution_filter import ExecutionFilter

    dss = DecisionSupportSystem()
    exec_filter = ExecutionFilter(max_drawdown=0.1)

    assert dss is not None
    assert exec_filter is not None
    assert trade_logger is not None
