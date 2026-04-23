"""
Unit tests for the 6-layer execution filter.
"""

from datetime import UTC, datetime

import pandas as pd
import pytest

from src.trading.execution_filter import ExecutionFilter
from src.trading.risk_manager import TradeSignal


@pytest.fixture
def base_market_data():
    """Create a basic DataFrame with required indicator columns."""
    data = {
        "atr_14": [1.0, 1.0],
        "atr_14_ma_100": [1.0, 1.0],
        "ema_20": [110.0, 111.0],
        "ema_50": [105.0, 106.0],
        "ema_200": [100.0, 100.5],
        "rsi_14": [55.0, 60.0],
    }
    return pd.DataFrame(data)


@pytest.fixture
def buy_signal():
    return TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1980.0,
        take_profit=2050.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8,
    )


@pytest.fixture
def sell_signal():
    return TradeSignal(
        symbol="XAUUSD",
        direction=-1,
        entry_price=2000.0,
        stop_loss=2020.0,
        take_profit=1950.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8,
    )


class TestExecutionFilter:
    def test_empty_market_data(self, buy_signal):
        filter_svc = ExecutionFilter()
        decision = filter_svc.validate(buy_signal, pd.DataFrame(), 0.0)
        assert not decision.approved
        assert decision.blocked_by == "Empty market data"

    def test_atr_volatility_pass(self, buy_signal, base_market_data):
        filter_svc = ExecutionFilter()
        # atr_14 (1.0) <= atr_14_ma_100 (1.0) * 3.0 -> Pass
        decision = filter_svc.validate(
            buy_signal,
            base_market_data,
            0.0,
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        )
        assert decision.approved

    def test_atr_volatility_fail(self, buy_signal, base_market_data):
        filter_svc = ExecutionFilter(atr_multiplier=1.0)
        base_market_data.loc[1, "atr_14"] = 5.0
        # atr_14 (5.0) > atr_14_ma_100 (1.0) * 1.0 -> Fail
        decision = filter_svc.validate(buy_signal, base_market_data, 0.0)
        assert not decision.approved
        assert decision.blocked_by == "ATR Volatility Spike"

    def test_trend_angle_buy_pass(self, buy_signal, base_market_data):
        filter_svc = ExecutionFilter()
        # ema_50: 105 -> 106 (slope +1) -> Pass for Buy
        decision = filter_svc.validate(
            buy_signal,
            base_market_data,
            0.0,
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        )
        assert decision.approved

    def test_trend_angle_buy_fail(self, buy_signal, base_market_data):
        filter_svc = ExecutionFilter()
        base_market_data.loc[1, "ema_50"] = 104.0
        # ema_50: 105 -> 104 (slope -1) -> Fail for Buy
        decision = filter_svc.validate(buy_signal, base_market_data, 0.0)
        assert not decision.approved
        assert decision.blocked_by == "Trend Angle Mismatch"

    def test_ema_sequence_buy_pass(self, buy_signal, base_market_data):
        filter_svc = ExecutionFilter()
        # 111 (ema20) > 106 (ema50) > 100.5 (ema200) -> Pass for Buy
        decision = filter_svc.validate(
            buy_signal,
            base_market_data,
            0.0,
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        )
        assert decision.approved

    def test_ema_sequence_buy_fail(self, buy_signal, base_market_data):
        filter_svc = ExecutionFilter()
        base_market_data.loc[1, "ema_20"] = 100.0
        # 100 (ema20) < 106 (ema50) -> Fail for Buy
        decision = filter_svc.validate(buy_signal, base_market_data, 0.0)
        assert not decision.approved
        assert decision.blocked_by == "EMA Sequence Mismatch"

    def test_momentum_buy_pass(self, buy_signal, base_market_data):
        filter_svc = ExecutionFilter()
        # rsi_14 (60) > 50 -> Pass for Buy
        decision = filter_svc.validate(
            buy_signal,
            base_market_data,
            0.0,
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        )
        assert decision.approved

    def test_momentum_buy_fail(self, buy_signal, base_market_data):
        filter_svc = ExecutionFilter()
        base_market_data.loc[1, "rsi_14"] = 45.0
        # rsi_14 (45) < 50 -> Fail for Buy
        decision = filter_svc.validate(buy_signal, base_market_data, 0.0)
        assert not decision.approved
        assert decision.blocked_by == "Momentum Mismatch"

    def test_session_filter_pass(self, buy_signal, base_market_data):
        filter_svc = ExecutionFilter()
        # 12:00 is between 08:00 and 21:00 -> Pass
        decision = filter_svc.validate(
            buy_signal,
            base_market_data,
            0.0,
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        )
        assert decision.approved

    def test_session_filter_fail(self, buy_signal, base_market_data):
        filter_svc = ExecutionFilter()
        # 02:00 is outside 08:00 and 21:00 -> Fail
        decision = filter_svc.validate(
            buy_signal,
            base_market_data,
            0.0,
            timestamp=datetime(2024, 1, 1, 2, 0, tzinfo=UTC),
        )
        assert not decision.approved
        assert decision.blocked_by == "Outside Trading Session"

    def test_drawdown_limit_pass(self, buy_signal, base_market_data):
        filter_svc = ExecutionFilter()
        # 0.1 < 0.15 -> Pass
        decision = filter_svc.validate(
            buy_signal,
            base_market_data,
            0.1,
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        )
        assert decision.approved

    def test_drawdown_limit_fail(self, buy_signal, base_market_data):
        filter_svc = ExecutionFilter()
        # 0.2 > 0.15 -> Fail
        decision = filter_svc.validate(buy_signal, base_market_data, 0.2)
        assert not decision.approved
        assert decision.blocked_by == "Circuit Breaker Active"

    def test_sell_signal_sequence_pass(self, sell_signal, base_market_data):
        filter_svc = ExecutionFilter()
        # For sell, we need ema20 < ema50 < ema200
        base_market_data.loc[1, "ema_20"] = 90.0
        base_market_data.loc[1, "ema_50"] = 95.0
        base_market_data.loc[1, "ema_200"] = 100.0
        # and slope of ema50 < 0: 105 -> 95
        # and RSI < 50
        base_market_data.loc[1, "rsi_14"] = 40.0

        decision = filter_svc.validate(
            sell_signal,
            base_market_data,
            0.0,
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        )
        assert decision.approved
