
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, UTC
import pandas as pd
from src.core.monitor import Monitor
from src.trading.execution_filter import ExecutionFilter, ExecutionDecision
from src.trading.audited_risk_manager import AuditedRiskManager
from src.core.schemas import TradeSignal
from src.core.constants import SignalDirection

@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.telegram_token.get_secret_value.return_value = ""
    cfg.prometheus_port = 8000
    cfg.volatility_extreme_threshold = 3.0
    cfg.min_confidence = 0.55
    cfg.signal_flicker_window = 6
    cfg.max_signal_changes = 3
    cfg.max_drawdown = 0.15
    cfg.max_positions = 5
    cfg.risk_per_trade = 0.01
    cfg.max_daily_loss = 0.05
    cfg.min_risk_reward = 1.5
    cfg.max_losing_streak = 3
    return cfg

def test_monitor_new_metrics(mock_config):
    monitor = Monitor(mock_config)

    with patch('src.core.monitor.MARKET_REGIME_GAUGE') as mock_regime_gauge, \
         patch('src.core.monitor.MARKET_VOLATILITY_GAUGE') as mock_vol_gauge, \
         patch('src.core.monitor.TECHNICAL_INDICATOR_GAUGE') as mock_tech_gauge, \
         patch('src.core.monitor.DECISION_FUNNEL_COUNTER') as mock_funnel_counter:

        monitor.log_market_context("TRENDING_UP", 1.5)
        # Check that it sets the current regime to 1 and others to 0
        assert mock_regime_gauge.labels.call_count >= 5
        mock_vol_gauge.set.assert_called_with(1.5)

        monitor.log_technical_indicator("rsi", 65.0)
        mock_tech_gauge.labels.assert_called_with(indicator="rsi")
        mock_tech_gauge.labels().set.assert_called_with(65.0)

        monitor.record_funnel_step("generated")
        mock_funnel_counter.labels.assert_called_with(stage="generated")
        mock_funnel_counter.labels().inc.assert_called()

def test_execution_filter_metrics(mock_config):
    monitor = MagicMock()
    ef = ExecutionFilter(config=mock_config, monitor=monitor)

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )

    # Mock technical checks to return specific values
    with patch.object(ef, '_check_atr_volatility_with_metrics', return_value=(True, {"ratio": 1.2})), \
         patch.object(ef, '_check_trend_angle_with_metrics', return_value=(True, {"slope": 0.5})), \
         patch.object(ef, '_check_momentum_with_metrics', return_value=(True, {"rsi": 60.0})), \
         patch.object(ef, '_check_session_time', return_value=True), \
         patch.object(ef, '_check_drawdown_limit', return_value=True), \
         patch.object(ef, '_check_confidence_threshold_with_metrics', return_value=(True, {"confidence": 0.8, "threshold": 0.55})), \
         patch.object(ef, '_check_signal_consistency_with_metrics', return_value=(True, {"changes": 0})), \
         patch.object(ef, '_check_macro_risk_with_metrics', return_value=(True, {"active_events": []})):

        ef.validate(signal)

        monitor.log_technical_indicator.assert_any_call("atr_ratio", 1.2)
        monitor.log_technical_indicator.assert_any_call("trend_slope", 0.5)
        monitor.log_technical_indicator.assert_any_call("rsi", 60.0)

def test_execution_filter_rejection_funnel(mock_config):
    monitor = MagicMock()
    ef = ExecutionFilter(config=mock_config, monitor=monitor)

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )

    # Force rejection by ATR
    with patch.object(ef, '_check_atr_volatility_with_metrics', return_value=(False, {"ratio": 5.0})):
        ef.validate(signal)
        monitor.record_funnel_step.assert_called_with("filter_rejected")

def test_audited_risk_manager_funnel(mock_config):
    monitor = MagicMock()
    arm = AuditedRiskManager(mock_config, account_balance=10000, monitor=monitor)

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )

    # Mock all checks to fail
    with patch.object(AuditedRiskManager, '_check_circuit_breaker', return_value=False):
        arm.approve(signal)
        monitor.record_funnel_step.assert_called_with("risk_rejected")
