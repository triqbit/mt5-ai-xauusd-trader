"""
Tests for Decision Support module.
"""
import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone
from src.core.decision_support import DecisionSupport, DecisionPacket
from src.trading.risk_manager import TradeSignal, RiskManager

@pytest.fixture
def mock_risk_manager():
    risk = MagicMock(spec=RiskManager)
    risk.peak_equity = 10000.0
    risk.balance = 9500.0
    risk.daily = MagicMock()
    risk.daily.realised_pnl = -100.0
    risk.daily.peak_equity = 10000.0
    risk.open_positions = {}
    risk.cfg = MagicMock()
    risk.cfg.max_daily_loss = 0.05
    risk.cfg.max_positions = 5
    return risk

@pytest.fixture
def sample_signal():
    return TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8
    )

def test_generate_packet(mock_risk_manager, sample_signal):
    ds = DecisionSupport(mock_risk_manager)
    consensus = {"ppo": 0.8, "lstm": 0.7}
    ohlcv_data = None  # Placeholder
    perf_metrics = {"win_rate": 0.6, "sharpe_ratio": 1.5}

    packet = ds.generate_packet(sample_signal, consensus, ohlcv_data, perf_metrics)

    assert isinstance(packet, DecisionPacket)
    assert packet.symbol == "XAUUSD"
    assert packet.signal.direction == 1
    assert packet.signal.confidence == 0.8
    assert packet.risk.is_approved is True
    assert packet.performance.win_rate == 0.6

def test_rejection_logic(mock_risk_manager, sample_signal):
    # Force a rejection by setting low confidence
    sample_signal.confidence = 0.4
    ds = DecisionSupport(mock_risk_manager)
    packet = ds.generate_packet(sample_signal, {}, None)

    assert packet.risk.is_approved is False
    assert "Confidence" in packet.risk.rejection_reason

def test_format_for_terminal(mock_risk_manager, sample_signal):
    ds = DecisionSupport(mock_risk_manager)
    packet = ds.generate_packet(sample_signal, {"ppo": 0.8}, None)
    panel = ds.format_for_terminal(packet)

    # panel.title might be a str or a Text object depending on rich version/usage
    title_str = str(panel.title)
    assert title_str.startswith("Decision Support Packet")

    # Verify it can be rendered to string to check for content
    from rich.console import Console
    console = Console(width=100)
    with console.capture() as capture:
        console.print(panel)
    output = capture.get()
    assert "XAUUSD" in output
    assert "BUY" in output
