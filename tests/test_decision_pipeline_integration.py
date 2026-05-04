"""
MT5 AI/ML Trading Bot - Decision Pipeline Integration Test
tests/test_decision_pipeline_integration.py

Verifies the unified decision pipeline:
Model Inference -> Risk Manager -> Execution Filter -> Signal Explainer -> Decision Support System
"""

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# Standardize mocks for use across all tests and imports
mock_torch = MagicMock()
# Scipy's array_api_compat checks issubclass(cls, torch.Tensor)
# We need to provide a real class to avoid TypeError
class MockTensor: pass
mock_torch.Tensor = MockTensor

mock_sb3 = MagicMock()
mock_talib = MagicMock()

with patch.dict("sys.modules", {
    "torch": mock_torch,
    "torch.nn": mock_torch.nn,
    "stable_baselines3": mock_sb3,
    "talib": mock_talib
}):
    from src.core.config import get_config
    from src.core.constants import SignalDirection
    from src.core.decision_support import DecisionSupportSystem
    from src.core.explainability import SignalExplainer
    from src.data.event_intelligence import RiskStatus
    from src.models import ensemble
    from src.models.ensemble import EnsembleModel
    from src.models.regime_detector import MarketRegime, RegimeInfo
    from src.trading.execution_filter import ExecutionFilter
    from src.trading.risk_manager import RiskManager, TradeSignal
    from src.utils.synthetic_data import ScenarioGenerator

@pytest.fixture
def mock_cfg():
    with patch.dict(os.environ, {
        "MT5_PASSWORD": "test_password",
        "MT5_SERVER": "test_server",
        "TELEGRAM_TOKEN": "123:abc",
        "TELEGRAM_CHAT_ID": "123456",
        "MODE": "demo"
    }):
        get_config.cache_clear()
        return get_config()

@pytest.fixture
def data_generator():
    return ScenarioGenerator(seed=42)

@pytest.fixture
def ensemble_model():
    with patch.object(ensemble, "torch", mock_torch), \
         patch.object(ensemble, "LSTMAttentionModel", MagicMock()):
        model = EnsembleModel(device="cpu")
        # Mock sub-models
        model._ppo_model = MagicMock()
        model._ppo_model.predict.return_value = (1, None) # Default BUY
        return model

@pytest.fixture
def risk_manager(mock_cfg):
    # Mocking TradeLogger and Monitor to avoid DB/network side effects
    return RiskManager(mock_cfg, account_balance=10000.0, logger_db=None, monitor=None)

@pytest.fixture
def execution_filter():
    return ExecutionFilter(max_drawdown=0.15)

@pytest.fixture
def explainer():
    return SignalExplainer()

@pytest.fixture
def dss():
    return DecisionSupportSystem()

def test_decision_pipeline_full_confluence(
    mock_cfg, data_generator, ensemble_model, risk_manager, execution_filter, explainer, dss
):
    """Case 1: Full Confluence - All components approve."""
    # 1. Market Data & Context
    df = data_generator.generate(n_steps=200, regime="trending")
    df.index = pd.date_range(start="2024-01-01", periods=200, freq="1min")

    # Enrich DF with expected columns for ExecutionFilter
    df["base_M5_ema_8"] = df["close"].ewm(span=8).mean()
    df["base_M5_ema_20"] = df["close"].ewm(span=20).mean()
    df["base_M5_ema_21"] = df["close"].ewm(span=21).mean()
    df["base_M5_ema_50"] = df["close"].ewm(span=50).mean()
    df["base_M5_ema_200"] = df["close"].ewm(span=200).mean()
    df["base_M5_rsi"] = 60.0 # Bullish momentum
    df["base_M5_atr"] = 1.0

    regime_info = RegimeInfo(
        label=MarketRegime.TRENDING,
        confidence=0.9,
        transition_score=0.1,
        volatility_index=1.0
    )

    # 2. Model Inference
    obs = np.random.rand(140)
    signal_obj = ensemble_model.predict(obs)
    assert signal_obj.direction == SignalDirection.BUY

    # 3. Risk Approval
    price = df["close"].iloc[-1]
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=signal_obj.direction.value,
        entry_price=price,
        stop_loss=price - 10.0,
        take_profit=price + 20.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=signal_obj.confidence
    )

    risk_approved = risk_manager.approve(signal)
    assert risk_approved is True

    # 4. Execution Filter
    filter_decision = execution_filter.validate(
        signal, df, current_drawdown=0.02, timestamp=datetime.now(timezone.utc)
    )
    assert filter_decision.is_approved is True

    # 5. Explainability
    risk_data = {
        "passed": risk_approved,
        "rejection_reasons": [],
        "risk_reward": 2.0,
        "summary": "Risk assessment passed"
    }

    regime_data = {
        "name": regime_info.label.value,
        "confidence": regime_info.confidence,
        "volatility": "Normal",
        "is_favorable": True
    }

    execution_data = {
        "passed": filter_decision.is_approved,
        "summary": "All filters passed",
        "filters": [{"name": "CONFLUENCE", "passed": True}]
    }

    explanation = explainer.explain(
        symbol=signal.symbol,
        direction=signal.direction,
        confidence=signal.confidence,
        model_votes=signal_obj.metadata["per_algo_votes"],
        model_weights=signal_obj.metadata["weights"],
        risk_data=risk_data,
        regime_info=regime_data,
        execution_data=execution_data
    )

    # 6. Decision Support Packet
    macro_risk = RiskStatus(is_blocked=False, active_events=[], reason="No macro risk")
    perf_metrics = {"sharpe_ratio": 1.5, "win_rate": 0.6}

    packet = dss.assemble_packet(
        signal.symbol, explanation, regime_info, macro_risk, perf_metrics
    )

    assert packet.is_executable is True
    assert len(packet.blocking_reasons) == 0
    assert "BUY" in packet.explanation.human_readable_summary

def test_decision_pipeline_risk_rejection(
    mock_cfg, data_generator, ensemble_model, risk_manager, execution_filter, explainer, dss
):
    """Case 2: Risk Rejection - Rejected due to low R:R."""
    df = data_generator.generate(n_steps=10)
    price = 2300.0

    # Low R:R (0.5)
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=price,
        stop_loss=price - 10.0,
        take_profit=price + 5.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8
    )

    risk_approved = risk_manager.approve(signal)
    assert risk_approved is False

    explanation = explainer.explain(
        symbol=signal.symbol,
        direction=signal.direction,
        confidence=0.8,
        model_votes={"ppo": 1},
        model_weights={"ppo": 1.0},
        risk_data={
            "passed": False,
            "rejection_reasons": ["Risk-Reward ratio too low"],
            "summary": "Rejected by RiskManager"
        },
        regime_info={"name": "Trending", "confidence": 0.8},
        execution_data={"passed": True, "summary": "Passed"}
    )

    packet = dss.assemble_packet(
        signal.symbol, explanation,
        RegimeInfo(label=MarketRegime.TRENDING, confidence=0.8, transition_score=0.1, volatility_index=1.0),
        RiskStatus(is_blocked=False, risk_multiplier=1.0, active_events=[], reason="OK"),
        {}
    )

    assert packet.is_executable is False
    assert any("Risk: Risk-Reward ratio too low" in r for r in packet.blocking_reasons)

def test_decision_pipeline_execution_block(
    mock_cfg, data_generator, ensemble_model, risk_manager, execution_filter, explainer, dss
):
    """Case 3: Execution Block - Rejected due to Trend Angle mismatch."""
    df = data_generator.generate(n_steps=50, regime="ranging")
    # For execution filter, Trend Angle uses EMA20 regression slope.
    # EMA Sequence check (8 > 21 > 50 > 200 for BUY) also runs.
    # We ensure EMA sequence passes but Trend Angle fails.
    df["base_M5_ema_8"] = 110.0
    df["base_M5_ema_21"] = 100.0
    df["base_M5_ema_50"] = 90.0
    df["base_M5_ema_200"] = 80.0
    # Force a downtrend in EMA20 for Trend Angle check
    df["base_M5_ema_20"] = np.linspace(100, 90, 50)

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1, # BUY
        entry_price=90.0,
        stop_loss=85.0,
        take_profit=100.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.7
    )

    filter_decision = execution_filter.validate(signal, df, current_drawdown=0.0)
    assert filter_decision.is_approved is False
    assert filter_decision.blocked_by == "TREND_ANGLE"

    explanation = explainer.explain(
        symbol=signal.symbol,
        direction=1,
        confidence=0.7,
        model_votes={"ppo": 1},
        model_weights={"ppo": 1.0},
        risk_data={"passed": True, "summary": "Passed"},
        regime_info={"name": "Ranging", "confidence": 0.5},
        execution_data={
            "passed": False,
            "summary": "TREND_ANGLE",
            "filters": [{"name": "TREND_ANGLE", "passed": False}]
        }
    )

    packet = dss.assemble_packet(
        signal.symbol, explanation,
        RegimeInfo(label=MarketRegime.RANGING, confidence=0.5, transition_score=0.1, volatility_index=1.2),
        RiskStatus(is_blocked=False, risk_multiplier=1.0, active_events=[], reason="OK"),
        {}
    )

    assert packet.is_executable is False
    assert any("Execution: TREND_ANGLE" in r for r in packet.blocking_reasons)

def test_decision_pipeline_macro_block(
    mock_cfg, explainer, dss
):
    """Case 4: Macro Block - Rejected due to active news events."""
    explanation = explainer.explain(
        symbol="XAUUSD",
        direction=1,
        confidence=0.9,
        model_votes={"ppo": 1},
        model_weights={"ppo": 1.0},
        risk_data={"passed": True, "summary": "Passed"},
        regime_info={"name": "Trending", "confidence": 0.9},
        execution_data={"passed": True, "summary": "Passed"}
    )

    macro_risk = RiskStatus(is_blocked=True, active_events=[], reason="Blocked by FOMC")

    packet = dss.assemble_packet(
        "XAUUSD", explanation,
        RegimeInfo(label=MarketRegime.TRENDING, confidence=0.9, transition_score=0.1, volatility_index=1.0),
        macro_risk,
        {}
    )

    assert packet.is_executable is False
    assert any("Macro: Blocked by FOMC" in r for r in packet.blocking_reasons)
