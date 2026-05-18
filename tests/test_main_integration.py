from unittest.mock import MagicMock

import pytest

from main import _prepare_trade_signal
from src.core.config import TradingConfig


@pytest.fixture
def cfg():
    return TradingConfig(MT5_PASSWORD="fake", MT5_SERVER="fake", risk_per_trade=0.01)


def test_prepare_trade_signal_with_macro_multiplier(cfg):
    risk_manager = MagicMock()
    # Mock size_position to return 0.1 lots
    risk_manager.size_position.return_value = 0.1

    allocator = MagicMock()
    alloc_result = MagicMock()
    alloc_result.is_allowed = True
    alloc_result.allocated_risk_pct = 0.01
    allocator.request_allocation.return_value = alloc_result

    # Case 1: No macro risk (multiplier = 1.0)
    signal_normal = _prepare_trade_signal(
        cfg=cfg,
        direction=1,
        confidence=0.8,
        price=2000.0,
        atr=10.0,
        risk=risk_manager,
        allocator=allocator,
        risk_multiplier=1.0,
    )
    assert signal_normal.lot_size == 0.1

    # Case 2: Macro risk reduction (multiplier = 0.5)
    signal_reduced = _prepare_trade_signal(
        cfg=cfg,
        direction=1,
        confidence=0.8,
        price=2000.0,
        atr=10.0,
        risk=risk_manager,
        allocator=allocator,
        risk_multiplier=0.5,
    )
    # 0.1 * 0.5 = 0.05
    assert signal_reduced.lot_size == 0.05

    # Case 3: Extreme macro risk reduction (multiplier = 0.1)
    signal_extreme = _prepare_trade_signal(
        cfg=cfg,
        direction=1,
        confidence=0.8,
        price=2000.0,
        atr=10.0,
        risk=risk_manager,
        allocator=allocator,
        risk_multiplier=0.1,
    )
    # 0.1 * 0.1 = 0.01
    assert signal_extreme.lot_size == 0.01
