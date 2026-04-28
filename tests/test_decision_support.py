"""
Tests for Decision Support module.
"""

import pytest
import pandas as pd
import numpy as np
from src.core.decision_support import DecisionSupport, DecisionPacket
from src.models.regime_detector import RegimeDetector, RegimeType, MarketRegime
from src.core.explainability import SignalExplainer, SignalExplanation

def test_regime_detector():
    detector = RegimeDetector(window=10)
    # Create mock data
    data = {
        "open": np.random.randn(20) + 2000,
        "high": np.random.randn(20) + 2005,
        "low": np.random.randn(20) + 1995,
        "close": np.random.randn(20) + 2000,
        "tick_volume": np.random.randint(100, 1000, 20)
    }
    df = pd.DataFrame(data)
    regime = detector.detect(df)

    assert isinstance(regime, MarketRegime)
    assert regime.label in RegimeType.__members__.values()
    assert 0.0 <= regime.confidence <= 1.0

def test_signal_explainer():
    explainer = SignalExplainer()
    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.75,
        regime_label="Trending",
        risk_passed=True,
        per_algo_votes={"ppo": 1.0, "lstm": 0.0}
    )

    assert isinstance(explanation, SignalExplanation)
    assert explanation.symbol == "XAUUSD"
    assert explanation.direction == 1
    assert "BUY" in explanation.summary
    assert len(explanation.attribution.clusters) > 0

def test_decision_support_packet_generation():
    ds = DecisionSupport()
    explainer = SignalExplainer()

    regime = MarketRegime(
        label=RegimeType.TRENDING,
        confidence=0.8,
        transition_score=0.1,
        features={"er": 0.7}
    )

    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.75,
        regime_label=regime.label,
        risk_passed=True,
        per_algo_votes={"ppo": 1.0}
    )

    packet = ds.generate_packet(
        symbol="XAUUSD",
        direction=1,
        confidence=0.75,
        price=2050.50,
        per_algo_votes={"ppo": 1.0},
        model_weights={"ppo": 1.0},
        regime=regime,
        risk_passed=True,
        rejection_reason=None,
        lot_size=0.1,
        risk_reward=2.0,
        equity_drawdown=0.02,
        recent_stats={"win_rate": 0.6, "profit_factor": 1.5, "consecutive_losses": 1},
        explanation=explanation
    )

    assert isinstance(packet, DecisionPacket)
    assert packet.signal.symbol == "XAUUSD"
    assert packet.signal.direction == 1
    assert packet.risk.passed is True
    assert packet.performance.recent_win_rate == 0.6
    assert "BUY XAUUSD" in packet.human_summary
