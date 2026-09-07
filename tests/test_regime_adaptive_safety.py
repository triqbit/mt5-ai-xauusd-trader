"""
Tests for Jules02 regime-adaptive safety hardening in ExecutionFilter.
Verifies that safety thresholds tighten during volatile/shock regimes.
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, UTC
import pandas as pd

from src.trading.execution_filter import ExecutionFilter, ExecutionDecision
from src.core.schemas import TradeSignal
from src.models.regime_detector import MarketRegime, RegimeInfo
from src.core.config import TradingConfig

@pytest.fixture
def mock_cfg():
    cfg = MagicMock(spec=TradingConfig)
    cfg.model_drift_threshold = 0.30
    cfg.model_accuracy_floor = 0.45
    cfg.min_confidence = 0.55
    cfg.volatility_extreme_threshold = 3.0
    cfg.signal_flicker_window = 6
    cfg.max_signal_changes = 3
    return cfg

@pytest.fixture
def execution_filter(mock_cfg):
    return ExecutionFilter(config=mock_cfg)

@pytest.fixture
def trade_signal():
    return TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        confidence=0.60, # Above standard 0.55, but below hardened 0.70
        algorithm="ensemble"
    )

def test_regime_adaptive_drift_tightening(execution_filter, mock_cfg):
    """Verify that drift threshold tightens in NEWS_SHOCK."""
    model_health = {"drift": 0.25, "accuracy": 0.80} # 0.25 is < 0.30 (standard) but > 0.20 (hardened)

    # 1. RANGING regime (standard)
    regime_ranging = RegimeInfo(
        label=MarketRegime.RANGING,
        confidence=0.9,
        transition_score=0.1,
        volatility_index=1.0
    )
    passed, metrics = execution_filter._check_model_stability_with_metrics(model_health, regime_info=regime_ranging)
    assert passed is True
    assert metrics["drift_threshold"] == 0.30

    # 2. NEWS_SHOCK regime (hardened)
    regime_news = RegimeInfo(
        label=MarketRegime.NEWS_SHOCK,
        confidence=0.9,
        transition_score=0.1,
        volatility_index=1.0
    )
    passed, metrics = execution_filter._check_model_stability_with_metrics(model_health, regime_info=regime_news)
    assert passed is False
    assert abs(metrics["drift_threshold"] - 0.20) < 1e-9 # 0.30 - 0.1

def test_regime_adaptive_accuracy_hardening(execution_filter, mock_cfg):
    """Verify that accuracy floor raises in VOLATILE_BREAKOUT."""
    model_health = {"drift": 0.05, "accuracy": 0.47} # 0.47 is > 0.45 (standard) but < 0.50 (hardened)

    # 1. RANGING regime (standard)
    regime_ranging = RegimeInfo(
        label=MarketRegime.RANGING,
        confidence=0.9,
        transition_score=0.1,
        volatility_index=1.0
    )
    passed, metrics = execution_filter._check_model_stability_with_metrics(model_health, regime_info=regime_ranging)
    assert passed is True
    assert metrics["accuracy_floor"] == 0.45

    # 2. VOLATILE_BREAKOUT regime (hardened)
    regime_breakout = RegimeInfo(
        label=MarketRegime.VOLATILE_BREAKOUT,
        confidence=0.9,
        transition_score=0.1,
        volatility_index=1.0
    )
    passed, metrics = execution_filter._check_model_stability_with_metrics(model_health, regime_info=regime_breakout)
    assert passed is False
    assert metrics["accuracy_floor"] == 0.50 # 0.45 + 0.05

def test_regime_adaptive_confidence_hardening(execution_filter, trade_signal):
    """Verify that confidence requirement raises in NEWS_SHOCK."""
    # trade_signal.confidence is 0.60

    # 1. RANGING regime (standard 0.55)
    regime_ranging = RegimeInfo(
        label=MarketRegime.RANGING,
        confidence=0.9,
        transition_score=0.1,
        volatility_index=1.0
    )
    passed, metrics = execution_filter._check_confidence_threshold_with_metrics(trade_signal, regime_info=regime_ranging)
    assert passed is True
    assert metrics["threshold"] == 0.55

    # 2. NEWS_SHOCK regime (hardened to 0.70)
    regime_news = RegimeInfo(
        label=MarketRegime.NEWS_SHOCK,
        confidence=0.9,
        transition_score=0.1,
        volatility_index=1.0
    )
    passed, metrics = execution_filter._check_confidence_threshold_with_metrics(trade_signal, regime_info=regime_news)
    assert passed is False
    assert metrics["threshold"] == 0.70

def test_regime_stability_layer(execution_filter):
    """Verify that high transition score blocks execution."""

    # 1. Stable regime
    regime_stable = RegimeInfo(
        label=MarketRegime.RANGING,
        confidence=0.9,
        transition_score=0.3,
        volatility_index=1.0
    )
    passed, metrics = execution_filter._check_regime_stability_with_metrics(regime_stable)
    assert passed is True
    assert metrics["transition_score"] == 0.3

    # 2. Unstable regime
    regime_unstable = RegimeInfo(
        label=MarketRegime.RANGING,
        confidence=0.9,
        transition_score=0.85,
        volatility_index=1.0
    )
    passed, metrics = execution_filter._check_regime_stability_with_metrics(regime_unstable)
    assert passed is False
    assert metrics["transition_score"] == 0.85

def test_full_validate_with_regime_info(execution_filter, trade_signal):
    """End-to-end check of validate method with regime_info."""
    # trade_signal.confidence = 0.60
    regime_news = RegimeInfo(
        label=MarketRegime.NEWS_SHOCK,
        confidence=0.9,
        transition_score=0.1,
        volatility_index=1.0
    )

    # Use precomputed to bypass technical indicators but keep model checks
    precomputed = {
        "atr_volatility": {"current_atr": 1.0, "avg_atr": 1.0, "ratio": 1.0},
        "trend_angle": {"slope": 1.0, "direction": 1},
        "ema_sequence": {"emas": {8: 104, 21: 103, 50: 102, 200: 101}, "direction": 1},
        "momentum": {"rsi": 60.0, "direction": 1},
    }

    decision = execution_filter.validate(
        trade_signal,
        precomputed_metrics=precomputed,
        regime_info=regime_news,
        timestamp=datetime(2023, 10, 10, 10, 0, 0, tzinfo=UTC)
    )

    assert decision.is_approved is False
    assert decision.blocked_by == "CONFIDENCE_THRESHOLD"
    assert decision.trace["confidence_threshold"]["threshold"] == 0.70
