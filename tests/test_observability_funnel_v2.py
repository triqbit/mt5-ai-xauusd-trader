from unittest.mock import MagicMock

import pytest

from src.core.constants import SignalDirection
from src.models.base_model import Signal
from src.models.ensemble import EnsembleModel
from src.models.regime_detector import MarketRegime, RegimeInfo


@pytest.fixture
def mock_monitor():
    return MagicMock()


@pytest.fixture
def ensemble(mock_monitor):
    return EnsembleModel(monitor=mock_monitor)


def test_ensemble_funnel_passed(ensemble, mock_monitor):
    signals = {
        "ppo": Signal(direction=SignalDirection.BUY, confidence=0.8),
        "lstm": Signal(direction=SignalDirection.BUY, confidence=0.7),
    }
    ensemble.aggregate_signals(signals)
    mock_monitor.record_signal_funnel.assert_called_with("ensemble", "passed")


def test_ensemble_funnel_dissent(ensemble, mock_monitor):
    signals = {
        "ppo": Signal(direction=SignalDirection.BUY, confidence=0.8),
        "lstm": Signal(direction=SignalDirection.SELL, confidence=0.7),
    }
    ensemble.aggregate_signals(signals)
    mock_monitor.record_signal_funnel.assert_called_with("ensemble", "dissent")


def test_ensemble_funnel_veto(ensemble, mock_monitor):
    # Need to meet consensus but trigger veto
    ensemble.dynamic_ensemble.weights = {"ppo": 0.7, "lstm": 0.3, "dreamer": 0.0}
    signals = {
        "ppo": Signal(direction=SignalDirection.BUY, confidence=0.8),
        "lstm": Signal(direction=SignalDirection.BUY, confidence=0.3),
    }
    # weighted_buy = 0.8*0.7 + 0.3*0.3 = 0.56 + 0.09 = 0.65 (>= 0.60 threshold)
    ensemble.aggregate_signals(signals)
    mock_monitor.record_signal_funnel.assert_called_with("ensemble", "veto")


def test_ensemble_funnel_hold(ensemble, mock_monitor):
    # consensus threshold is 0.6 by default
    ensemble.dynamic_ensemble.weights = {"ppo": 1.0}
    signals = {"ppo": Signal(direction=SignalDirection.BUY, confidence=0.5)}
    ensemble.aggregate_signals(signals)
    mock_monitor.record_signal_funnel.assert_called_with("ensemble", "hold")


def test_ensemble_funnel_market_instability(ensemble, mock_monitor):
    regime = RegimeInfo(
        label=MarketRegime.TRENDING,
        confidence=0.1,  # Very low
        volatility_index=1.0,
        session_alignment=0.1,
        volatility_alignment=0.1,
        transition_score=0.9,
    )
    # context_stability = mean(0.1, 0.1, 0.1, 1.0 - 0.9) = 0.1 < 0.4
    signals = {"ppo": Signal(direction=SignalDirection.BUY, confidence=0.9)}
    ensemble.aggregate_signals(signals, regime_info=regime)
    mock_monitor.record_signal_funnel.assert_called_with("ensemble", "hold")
