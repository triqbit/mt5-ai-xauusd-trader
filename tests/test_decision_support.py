
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from src.core.decision_support import DecisionSupport, DecisionPacket, PerformanceContext
from src.core.explainability import SignalDirection, SignalExplanation, RiskAssessment, RegimeContext
from src.models.regime_detector import RegimeInfo, MarketRegime
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
    trade_logger, risk_manager, _, _ = mock_components

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
