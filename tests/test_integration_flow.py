"""Integration tests for the full trading flow."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.core.config import TradingConfig
from src.core.trade_logger import TradeLogger
from src.core.monitor import Monitor
from src.trading.risk_engine import RiskEngine, TradeSignal
from src.trading.mt5_connector import MT5Connector
from src.models.ensemble import EnsembleModel

@pytest.fixture
def mock_components():
    cfg = MagicMock(spec=TradingConfig)
    cfg.symbol = "XAUUSD"
    cfg.risk_per_trade = 0.01
    cfg.confidence_threshold = 0.55
    cfg.consensus_threshold = 0.60
    cfg.max_positions = 5
    cfg.drawdown_levels = {1: 0.1, 2: 0.15, 3: 0.2, 4: 0.25, 5: 0.3}
    cfg.daily_loss_levels = {1: 0.02, 2: 0.03, 3: 0.04, 4: 0.05}
    cfg.max_losing_streak = 3

    connector = MagicMock(spec=MT5Connector)
    trade_logger = MagicMock(spec=TradeLogger)
    monitor = MagicMock(spec=Monitor)
    risk = RiskEngine(cfg, account_balance=10000.0, logger_db=trade_logger, monitor=monitor)
    model = EnsembleModel(device="cpu", consensus_threshold=0.6)

    return cfg, connector, trade_logger, monitor, risk, model

def test_full_signal_to_order_flow(mock_components):
    cfg, connector, trade_logger, monitor, risk, model = mock_components

    # 1. Mock model prediction
    with patch.object(model, 'predict', return_value=(1, 0.8, {"ppo": 1.0})):
        import numpy as np
        direction, confidence, per_algo = model.predict(np.zeros(140))

        # 2. Create signal
        signal = TradeSignal(
            symbol=cfg.symbol,
            direction=direction,
            entry_price=2300.0,
            stop_loss=2290.0,
            take_profit=2320.0,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=confidence
        )

        # 3. Risk approval
        if risk.approve_signal(signal):
            # 4. Place order
            connector.place_order(signal)

    connector.place_order.assert_called_once_with(signal)

def test_flow_rejection_low_confidence(mock_components):
    cfg, connector, trade_logger, monitor, risk, model = mock_components

    with patch.object(model, 'predict', return_value=(1, 0.5, {"ppo": 1.0})):
        direction, confidence, per_algo = model.predict(None)
        signal = TradeSignal(
            symbol=cfg.symbol, direction=direction, entry_price=2300.0,
            stop_loss=2290.0, take_profit=2320.0, lot_size=0.1,
            algorithm="ensemble", confidence=confidence
        )
        approved = risk.approve_signal(signal)
        assert approved is False
        connector.place_order.assert_not_called()

def test_flow_halted_by_drawdown(mock_components):
    cfg, connector, trade_logger, monitor, risk, model = mock_components

    # Trigger Level 5 drawdown
    risk.update_performance(current_equity=6000.0) # 40% DD
    assert risk.trading_halted is True

    signal = TradeSignal(
        symbol=cfg.symbol, direction=1, entry_price=2300.0,
        stop_loss=2290.0, take_profit=2320.0, lot_size=0.1,
        algorithm="ensemble", confidence=0.9
    )
    assert risk.approve_signal(signal) is False
