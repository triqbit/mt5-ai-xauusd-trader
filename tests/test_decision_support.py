
from unittest.mock import MagicMock, patch

import pytest

from src.core.decision_support import DecisionPacket, DecisionSupport, PerformanceContext
from src.core.explainability import (
    RegimeContext,
    RiskAssessment,
    SignalDirection,
    SignalExplanation,
)
from src.models.regime_detector import MarketRegime, RegimeInfo
from src.trading.risk_manager import TradeSignal


@pytest.fixture
def mock_components():
    trade_logger = MagicMock()
    trade_logger.read_performance_report.return_value = {
        "sharpe_ratio": 1.5,
        "profit_factor": 2.1,
        "max_drawdown": 0.1,
        "win_rate": 0.6,
        "total_trades": 100
    }

    risk_manager = MagicMock()
    risk_manager.daily.realised_pnl = 500.0
    risk_manager._get_rejection_reason.return_value = []

    regime_detector = MagicMock()

    signal_explainer = MagicMock()

    return trade_logger, risk_manager, regime_detector, signal_explainer

@pytest.fixture
def decision_support(mock_components):
    return DecisionSupport(*mock_components)

def test_generate_packet(decision_support, mock_components):
    _ = mock_components

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8
    )

    regime_info = RegimeInfo(
        label=MarketRegime.TRENDING,
        confidence=0.9,
        transition_score=0.1,
        volatility_index=1.2
    )

    explanation = SignalExplanation(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        total_confidence=0.8,
        model_attributions=[],
        feature_contributions=[],
        risk_assessment=RiskAssessment(
            passed=True,
            risk_reward_ratio=2.0,
            drawdown_impact_pct=0.01,
            summary="Risk passed"
        ),
        regime_context=RegimeContext(
            regime_name="Trending",
            confidence=0.9,
            volatility_state="Normal",
            is_favorable=True,
            summary="Market trending up"
        ),
        human_readable_summary="Explanation summary",
        machine_attribution={}
    )

    packet = decision_support.generate_packet(signal, regime_info, explanation)

    assert isinstance(packet, DecisionPacket)
    assert packet.symbol == "XAUUSD"
    assert packet.direction == SignalDirection.BUY
    assert packet.risk_approved is True
    assert packet.performance.sharpe_ratio == 1.5
    assert packet.performance.recent_pnl == 500.0

def test_format_for_terminal(decision_support):
    regime_info = RegimeInfo(
        label=MarketRegime.TRENDING,
        confidence=0.9,
        transition_score=0.1,
        volatility_index=1.2
    )

    performance = PerformanceContext(
        sharpe_ratio=1.5,
        profit_factor=2.1,
        max_drawdown=0.1,
        win_rate=0.6,
        total_trades=100,
        recent_pnl=500.0
    )

    explanation = SignalExplanation(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        total_confidence=0.8,
        model_attributions=[],
        feature_contributions=[],
        risk_assessment=RiskAssessment(
            passed=True,
            risk_reward_ratio=2.0,
            drawdown_impact_pct=0.01,
            summary="Risk passed"
        ),
        regime_context=RegimeContext(
            regime_name="Trending",
            confidence=0.9,
            volatility_state="Normal",
            is_favorable=True,
            summary="Market trending up"
        ),
        human_readable_summary="Explanation summary",
        machine_attribution={}
    )

    packet = DecisionPacket(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        confidence=0.8,
        model_consensus={"PPO": "BUY", "LSTM": "BUY"},
        regime=regime_info,
        risk_approved=True,
        blocked_reasons=[],
        risk_reward_ratio=2.0,
        lot_size=0.1,
        performance=performance,
        explanation=explanation,
        human_summary="✅ APPROVED BUY XAUUSD"
    )

    output = decision_support.format_for_terminal(packet)
    assert "Institutional Decision Support" in output
    assert "XAUUSD" in output
    assert "TRENDING" in output

def test_format_for_terminal_with_rejections(decision_support, packet):
    packet.risk_approved = False
    packet.blocked_reasons = ["Circuit breaker active"]
    packet.human_summary = "❌ BLOCKED BUY XAUUSD"

    output = decision_support.format_for_terminal(packet)
    assert "Circuit breaker active" in output
    assert "FAIL" in output

def test_format_for_terminal_fallback(decision_support, packet):
    # Mock rich to simulate its absence
    with patch.dict("sys.modules", {"rich": None, "rich.console": None, "rich.panel": None, "rich.table": None, "rich.box": None, "rich.layout": None}):
        output = decision_support.format_for_terminal(packet)
        assert "=== DECISION PACKET: XAUUSD ===" in output
        assert "✅ APPROVED BUY XAUUSD" in output

def test_format_for_terminal_fallback_with_rejections(decision_support, packet):
    packet.risk_approved = False
    packet.blocked_reasons = ["Circuit breaker active"]
    packet.human_summary = "❌ BLOCKED BUY XAUUSD"

    # Mock rich to simulate its absence
    with patch.dict("sys.modules", {"rich": None, "rich.console": None, "rich.panel": None, "rich.table": None, "rich.box": None, "rich.layout": None}):
        output = decision_support.format_for_terminal(packet)
        assert "=== DECISION PACKET: XAUUSD ===" in output
        assert "Blocked Reasons: Circuit breaker active" in output

@pytest.fixture
def packet():
    regime_info = RegimeInfo(
        label=MarketRegime.TRENDING,
        confidence=0.9,
        transition_score=0.1,
        volatility_index=1.2
    )

    performance = PerformanceContext(
        sharpe_ratio=1.5,
        profit_factor=2.1,
        max_drawdown=0.1,
        win_rate=0.6,
        total_trades=100,
        recent_pnl=500.0
    )

    explanation = SignalExplanation(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        total_confidence=0.8,
        model_attributions=[],
        feature_contributions=[],
        risk_assessment=RiskAssessment(
            passed=True,
            risk_reward_ratio=2.0,
            drawdown_impact_pct=0.01,
            summary="Risk passed"
        ),
        regime_context=RegimeContext(
            regime_name="Trending",
            confidence=0.9,
            volatility_state="Normal",
            is_favorable=True,
            summary="Market trending up"
        ),
        human_readable_summary="Explanation summary",
        machine_attribution={}
    )

    return DecisionPacket(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        confidence=0.8,
        model_consensus={"PPO": "BUY", "LSTM": "BUY"},
        regime=regime_info,
        risk_approved=True,
        blocked_reasons=[],
        risk_reward_ratio=2.0,
        lot_size=0.1,
        performance=performance,
        explanation=explanation,
        human_summary="✅ APPROVED BUY XAUUSD"
    )

def test_generate_packet_fallback_risk(mock_components):
    _, risk_manager, _, _ = mock_components
    # Temporarily remove _get_rejection_reason to test fallback
    del risk_manager._get_rejection_reason

    ds = DecisionSupport(*mock_components)

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8
    )

    regime_info = RegimeInfo(
        label=MarketRegime.TRENDING,
        confidence=0.9,
        transition_score=0.1,
        volatility_index=1.2
    )

    explanation = SignalExplanation(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        total_confidence=0.8,
        model_attributions=[],
        feature_contributions=[],
        risk_assessment=RiskAssessment(
            passed=False,
            rejection_reasons=["Test rejection"],
            risk_reward_ratio=2.0,
            drawdown_impact_pct=0.01,
            summary="Risk failed"
        ),
        regime_context=RegimeContext(
            regime_name="Trending",
            confidence=0.9,
            volatility_state="Normal",
            is_favorable=True,
            summary="Market trending up"
        ),
        human_readable_summary="Explanation summary",
        machine_attribution={}
    )

    packet = ds.generate_packet(signal, regime_info, explanation)
    assert packet.risk_approved is False
    assert packet.blocked_reasons == ["Test rejection"]
