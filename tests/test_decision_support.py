import pytest
from datetime import datetime, timezone
from src.core.decision_support import DecisionPacket, DecisionSupport
from src.core.explainability import SignalExplanation, SignalExplainer
from src.models.dynamic_ensemble import MarketRegime

def test_decision_packet_creation():
    packet = DecisionPacket(
        symbol="XAUUSD",
        direction=1,
        confidence=0.85,
        model_consensus={"ppo": 0.9, "lstm": 0.8},
        market_regime=MarketRegime.TRENDING,
        risk_state="STABLE",
        is_blocked=False,
        performance_context={"sharpe": 2.1, "win_rate": 0.65}
    )
    assert packet.symbol == "XAUUSD"
    assert packet.direction == 1
    assert packet.confidence == 0.85
    assert packet.market_regime == MarketRegime.TRENDING
    assert not packet.is_blocked

def test_decision_packet_to_human_readable():
    explanation = SignalExplanation(
        symbol="XAUUSD",
        direction=1,
        features={"rsi": 30.0, "mavg": 1.2},
        contributions={"rsi": "POSITIVE", "mavg": "POSITIVE"},
        summary="Oversold conditions on RSI"
    )
    packet = DecisionPacket(
        symbol="XAUUSD",
        direction=1,
        confidence=0.85,
        model_consensus={"ppo": 0.9, "lstm": 0.8},
        market_regime=MarketRegime.TRENDING,
        risk_state="STABLE",
        is_blocked=False,
        performance_context={"sharpe": 2.1, "win_rate": 0.65},
        explanation=explanation
    )
    readable = packet.to_human_readable()
    assert "INSTITUTIONAL DECISION PACKET" in readable
    assert "XAUUSD" in readable
    assert "BUY" in readable
    assert "85.0%" in readable
    assert "TRENDING" in readable
    assert "Oversold conditions on RSI" in readable

def test_decision_packet_rejected():
    packet = DecisionPacket(
        symbol="XAUUSD",
        direction=-1,
        confidence=0.7,
        model_consensus={"ppo": 0.7, "lstm": 0.7},
        market_regime=MarketRegime.RANGING,
        risk_state="WARNING",
        is_blocked=True,
        block_reasons=["Daily loss limit reached"],
        performance_context={"sharpe": 1.5, "win_rate": 0.55}
    )
    readable = packet.to_human_readable()
    assert "❌ REJECTED" in readable
    assert "Daily loss limit reached" in readable

def test_decision_support_generate():
    ds = DecisionSupport()
    packet = ds.generate_packet(
        symbol="XAUUSD",
        direction=1,
        confidence=0.9,
        model_consensus={"ppo": 0.9},
        market_regime=MarketRegime.TRENDING,
        risk_state="STABLE",
        is_blocked=False,
        block_reasons=[],
        performance_context={"win_rate": 0.7}
    )
    assert isinstance(packet, DecisionPacket)
    assert packet.confidence == 0.9

def test_signal_explainer():
    explainer = SignalExplainer()
    explanation = explainer.explain("XAUUSD", 1, {"f1": 1.5, "f2": -0.5, "f3": 0.0})
    assert explanation.contributions["f1"] == "POSITIVE"
    assert explanation.contributions["f2"] == "NEGATIVE"
    assert explanation.contributions["f3"] == "NEUTRAL"
