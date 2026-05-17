"""
MT5 AI/ML Trading Bot - Adaptive Feedback Loop Integration Test
tests/test_adaptive_feedback_loop.py

Verifies the high-value system path:
Market Outcome -> DynamicEnsemble Adaptation -> Ensemble Confidence Penalty -> Execution Filter Safety Block -> Audit Traceability
"""

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import select

from src.core.audit_log import AuditEntry, AuditLogger
from src.core.config import get_config
from src.core.constants import SignalDirection
from src.core.schemas import TradeSignal
from src.core.trade_logger import TradeLogger
from src.models.base_model import Signal
from src.models.ensemble import EnsembleModel
from src.trading.execution_filter import ExecutionFilter


@pytest.fixture
def system_env(tmp_path):
    """Sets up a temporary environment for integration testing."""
    db_path = tmp_path / "system.db"
    audit_db_path = tmp_path / "audit.db"

    env_vars = {
        "MT5_PASSWORD": "test_password",
        "MT5_SERVER": "test_server",
        "TELEGRAM_TOKEN": "123:abc",
        "TELEGRAM_CHAT_ID": "123456",
        "MODE": "demo",
        "DATABASE_URL": f"sqlite:///{db_path}",
        "MODEL_DRIFT_THRESHOLD": "0.3",
        "MODEL_ACCURACY_FLOOR": "0.5"
    }

    with patch.dict(os.environ, env_vars):
        get_config.cache_clear()
        cfg = get_config()

        # Reset Singletons if any
        AuditLogger._instance = None
        AuditLogger._initialized = False
        audit_logger = AuditLogger(db_url=f"sqlite:///{audit_db_path}")
        trade_logger = TradeLogger(db_url=f"sqlite:///{db_path}")

        yield cfg, audit_logger, trade_logger

@pytest.fixture
def ensemble(system_env):
    cfg, _, _ = system_env
    # Mocking sub-agents to avoid heavy imports or weight loading
    model = EnsembleModel(config=cfg)
    model.ppo_agent = MagicMock()
    model.dreamer_agent = MagicMock()
    model.lstm_model = MagicMock()

    # Set default behaviors
    model.ppo_agent.predict.return_value = Signal(direction=SignalDirection.BUY, confidence=0.9)
    model.dreamer_agent.predict.return_value = Signal(direction=SignalDirection.BUY, confidence=0.9)
    model.lstm_model.predict.return_value = Signal(direction=SignalDirection.BUY, confidence=0.9)

    return model

@pytest.fixture
def execution_filter(system_env):
    cfg, _, _ = system_env
    return ExecutionFilter(max_drawdown=0.15, config=cfg)

def test_adaptive_feedback_loop_end_to_end(system_env, ensemble, execution_filter):
    """
    Test Path: Outcome -> Adapt -> Penalty -> Block -> Audit
    1. System starts healthy.
    2. Multiple incorrect outcomes are observed.
    3. Ensemble applies confidence penalty.
    4. ExecutionFilter eventually blocks trade due to MODEL_STABILITY.
    5. Audit trail records the entire degradation.
    """
    cfg, audit_logger, _trade_logger = system_env

    # Mock market data for ExecutionFilter (Trend matching BUY)
    df = pd.DataFrame({
        "high": [2000.0 + i for i in range(200)],
        "low": [1990.0 + i for i in range(200)],
        "close": [1995.0 + i for i in range(200)],
    })
    # Add indicators to pass filters
    df["base_M5_ema_8"] = df["close"].ewm(span=8).mean()
    df["base_M5_ema_21"] = df["close"].ewm(span=21).mean()
    df["base_M5_ema_50"] = df["close"].ewm(span=50).mean()
    df["base_M5_ema_200"] = df["close"].ewm(span=200).mean()
    df["base_M5_atr"] = 5.0
    df["base_M5_rsi"] = 60.0

    # 1. Healthy State Baseline
    obs = np.random.rand(140)
    sig_obj = ensemble.predict(obs, symbol=cfg.symbol)
    assert sig_obj.confidence == pytest.approx(0.9)

    # Use a fixed Wednesday timestamp to avoid SESSION_CLOSED
    fixed_ts = datetime(2024, 5, 22, 12, 0, tzinfo=timezone.utc)

    signal = TradeSignal(
        symbol=cfg.symbol,
        direction=sig_obj.direction.value,
        entry_price=2100.0,
        stop_loss=2090.0,
        take_profit=2120.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=sig_obj.confidence,
        timestamp=fixed_ts
    )

    decision = execution_filter.validate(signal, df, current_drawdown=0.01, timestamp=fixed_ts)
    assert decision.is_approved is True

    # 2. Simulate Performance Degradation (Phase 1: Baseline then outcomes)
    # Feed 20 CORRECT outcomes to establish a high baseline
    for _ in range(20):
        ensemble.predict(obs, symbol=cfg.symbol)
        ensemble.observe_outcome(SignalDirection.BUY)

    # Observe 10 incorrect outcomes to trigger significant drift
    # EnsembleModel.observe_outcome calls DynamicEnsemble.record_outcome
    for _ in range(10):
        # Model predicted BUY (above), so we give it SELL outcomes
        ensemble.predict(obs, symbol=cfg.symbol)
        ensemble.observe_outcome(SignalDirection.SELL)

    # 3. Verify Confidence Penalty (Phase 2: Prediction)
    # Drift should now be high.
    # Penalty trigger is 50% of threshold (0.3 * 0.5 = 0.15)
    # Drift = (acc - recent_acc) * 2.
    # Long term acc was high (if initialized equal), now it's dropping.
    health = ensemble.get_health_metrics()
    assert health["drift"] > 0.15

    sig_obj_degraded = ensemble.predict(obs, symbol=cfg.symbol)
    # Confidence was 0.9, should now be penalized
    assert sig_obj_degraded.confidence < 0.9
    assert "drift_penalty" in sig_obj_degraded.metadata

    # 4. Verify Execution Block (Phase 3: Safety Gating)
    # Feed even more bad outcomes to push drift over 0.3 or accuracy below 0.5
    for _ in range(20):
        ensemble.predict(obs, symbol=cfg.symbol)
        ensemble.observe_outcome(SignalDirection.SELL)

    health_critical = ensemble.get_health_metrics()
    # model_stability = (drift < threshold) and (accuracy >= floor)
    # threshold=0.3, floor=0.5
    assert health_critical["drift"] >= 0.3 or health_critical["accuracy"] < 0.5

    signal_blocked = TradeSignal(
        symbol=cfg.symbol,
        direction=sig_obj_degraded.direction.value,
        entry_price=2100.0,
        stop_loss=2090.0,
        take_profit=2120.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=sig_obj_degraded.confidence,
        timestamp=fixed_ts
    )

    # Log to audit (simulating main.py behavior)
    audit_logger.log_prediction(
        symbol=cfg.symbol,
        direction=sig_obj_degraded.direction.value,
        confidence=sig_obj_degraded.confidence,
        model_metadata=sig_obj_degraded.metadata
    )

    decision_blocked = execution_filter.validate(
        signal_blocked,
        df,
        current_drawdown=0.01,
        model_health=health_critical,
        timestamp=fixed_ts
    )

    assert decision_blocked.is_approved is False
    assert decision_blocked.blocked_by == "MODEL_STABILITY"

    # Log execution decision to audit
    audit_logger.log_execution_decision(
        symbol=cfg.symbol,
        direction=signal_blocked.direction,
        trace=decision_blocked.trace,
        is_approved=decision_blocked.is_approved
    )

    # 5. Verify Traceability (Phase 4: Audit Verification)
    with audit_logger.Session() as session:
        # Verify prediction entry with penalty
        penalty_entry = session.execute(
            select(AuditEntry).where(AuditEntry.action == "prediction")
        ).scalars().all()[-1]
        assert "drift_penalty" in penalty_entry.metadata_json["model_context"]

        # Verify execution decision block
        block_entry = session.execute(
            select(AuditEntry).where(AuditEntry.actor == "execution_filter")
        ).scalars().one()
        assert block_entry.metadata_json["is_approved"] is False
        assert block_entry.metadata_json["trace"]["model_stability"]["passed"] is False
        assert block_entry.metadata_json["trace"]["model_stability"]["drift"] == health_critical["drift"]

def test_recovery_after_stabilization(system_env, ensemble, execution_filter):
    """Verifies that if outcomes improve, the system recovers and allows trading again."""
    cfg, _audit_logger, _ = system_env
    # Increasing price for TREND_ANGLE
    df = pd.DataFrame({
        "high": [2000.0 + i for i in range(100)],
        "low": [1990.0 + i for i in range(100)],
        "close": [1995.0 + i for i in range(100)],
    })
    df["base_M5_ema_8"] = df["close"].ewm(span=8).mean()
    df["base_M5_ema_21"] = df["close"].ewm(span=21).mean()
    df["base_M5_ema_50"] = df["close"].ewm(span=50).mean()
    df["base_M5_ema_200"] = df["close"].ewm(span=200).mean()
    df["base_M5_atr"] = 5.0
    df["base_M5_rsi"] = 60.0

    obs = np.random.rand(140)
    fixed_ts = datetime(2024, 5, 22, 12, 0, tzinfo=timezone.utc)

    # 1. Force degraded state
    for _ in range(50):
        ensemble.predict(obs, symbol=cfg.symbol)
        ensemble.observe_outcome(SignalDirection.SELL)

    health = ensemble.get_health_metrics()
    assert health["accuracy"] < 0.5 or health["drift"] > 0.3

    # 2. Feed many "CORRECT" outcomes
    for _ in range(100):
        ensemble.predict(obs, symbol=cfg.symbol)
        ensemble.observe_outcome(SignalDirection.BUY)

    health_recovered = ensemble.get_health_metrics()
    assert health_recovered["accuracy"] >= 0.5
    assert health_recovered["drift"] < 0.3

    # 3. Assert approval
    obs = np.random.rand(140)
    sig = ensemble.predict(obs)
    trade_sig = TradeSignal(
        symbol=cfg.symbol, direction=sig.direction.value, entry_price=2100.0,
        stop_loss=2090.0, take_profit=2120.0, lot_size=0.1, algorithm="ensemble",
        confidence=sig.confidence,
        timestamp=fixed_ts
    )

    decision = execution_filter.validate(trade_sig, df, 0.01, model_health=health_recovered, timestamp=fixed_ts)
    assert decision.is_approved is True
