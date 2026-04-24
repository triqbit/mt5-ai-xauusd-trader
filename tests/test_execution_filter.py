
import pytest
import pandas as pd
from datetime import datetime, timezone
from src.trading.execution_filter import ExecutionFilter, ExecutionDecision
from src.trading.risk_manager import TradeSignal

@pytest.fixture
def base_indicators():
    return pd.DataFrame({
        "atr_14": [1.0, 1.0],
        "atr_14_ma_100": [1.0, 1.0],
        "ema_50": [100.0, 101.0],  # Upward slope
        "ema_20": [105.0, 106.0],
        "ema_200": [90.0, 91.0],
        "rsi_14": [60.0, 60.0]
    })

@pytest.fixture
def buy_signal():
    return TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )

class TestExecutionFilter:
    def test_layer1_volatility_block(self, buy_signal, base_indicators):
        filter = ExecutionFilter()
        # High volatility
        base_indicators.loc[1, "atr_14"] = 4.0
        base_indicators.loc[1, "atr_14_ma_100"] = 1.0

        decision = filter.validate(buy_signal, base_indicators, 0.0)
        assert not decision.is_approved
        assert "Volatility" in decision.blocked_by

    def test_layer2_trend_angle(self, buy_signal, base_indicators):
        filter = ExecutionFilter()
        # Downward slope for buy signal
        base_indicators.loc[1, "ema_50"] = 99.0

        decision = filter.validate(buy_signal, base_indicators, 0.0)
        assert not decision.is_approved
        assert "Trend: EMA50 slope mismatch" in decision.blocked_by

    def test_layer3_ema_sequence(self, buy_signal, base_indicators):
        filter = ExecutionFilter()
        # Wrong sequence for buy: 20 < 50
        base_indicators.loc[1, "ema_20"] = 95.0
        base_indicators.loc[1, "ema_50"] = 101.0

        decision = filter.validate(buy_signal, base_indicators, 0.0)
        assert not decision.is_approved
        assert "Trend: EMA sequence mismatch" in decision.blocked_by

    def test_layer4_momentum(self, buy_signal, base_indicators):
        filter = ExecutionFilter()
        # RSI < 50 for buy
        base_indicators.loc[1, "rsi_14"] = 40.0

        decision = filter.validate(buy_signal, base_indicators, 0.0)
        assert not decision.is_approved
        assert "Momentum" in decision.blocked_by

    def test_layer5_session(self, buy_signal, base_indicators):
        filter = ExecutionFilter()
        # 03:00 UTC (Outside 08-21)
        ts = datetime(2023, 1, 1, 3, 0, 0, tzinfo=timezone.utc)

        decision = filter.validate(buy_signal, base_indicators, 0.0, timestamp=ts)
        assert not decision.is_approved
        assert "Session" in decision.blocked_by

    def test_layer6_drawdown(self, buy_signal, base_indicators):
        filter = ExecutionFilter(drawdown_threshold=0.15)

        decision = filter.validate(buy_signal, base_indicators, 0.16)
        assert not decision.is_approved
        assert "Drawdown" in decision.blocked_by

    def test_full_cascade_approval(self, buy_signal, base_indicators):
        filter = ExecutionFilter()
        ts = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        decision = filter.validate(buy_signal, base_indicators, 0.05, timestamp=ts)
        assert decision.is_approved
        assert decision.blocked_by is None
        assert decision.confidence == buy_signal.confidence

    def test_sell_signal_validation(self, base_indicators):
        sell_signal = TradeSignal(
            symbol="XAUUSD",
            direction=-1,
            entry_price=2000.0,
            stop_loss=2010.0,
            take_profit=1980.0,
            lot_size=0.1,
            algorithm="test",
            confidence=0.7
        )
        # Setup indicators for sell
        indicators = pd.DataFrame({
            "atr_14": [1.0, 1.0],
            "atr_14_ma_100": [1.0, 1.0],
            "ema_50": [100.0, 99.0],    # Down slope
            "ema_20": [95.0, 94.0],      # 20 < 50
            "ema_200": [110.0, 109.0],   # 50 < 200 (Sequence: 20 < 50 < 200)
            "rsi_14": [40.0, 40.0]       # RSI < 50
        })

        filter = ExecutionFilter()
        ts = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        decision = filter.validate(sell_signal, indicators, 0.0, timestamp=ts)

        assert decision.is_approved
        assert decision.blocked_by is None
