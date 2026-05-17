"""
Tests for structured execution filter traceability.
"""

import pandas as pd
import pytest

from src.core.audit_log import AuditEntry, AuditLogger
from src.core.schemas import TradeSignal
from src.trading.execution_filter import ExecutionDecision, ExecutionFilter


class MockConfig:
    def __init__(self):
        self.model_drift_threshold = 0.3
        self.model_accuracy_floor = 0.45
        self.model_win_rate_floor = 0.40
        self.min_confidence = 0.6
        self.logs_dir = "logs"
        self.signal_flicker_window = 6
        self.max_signal_changes = 3

@pytest.fixture
def execution_filter():
    cfg = MockConfig()
    return ExecutionFilter(max_drawdown=0.15, config=cfg)

@pytest.fixture
def audit_logger(tmp_path):
    db_path = tmp_path / "audit.db"
    return AuditLogger(db_url=f"sqlite:///{db_path}")

def test_execution_filter_full_trace(execution_filter):
    """Verify that ExecutionFilter evaluates all layers and returns a full trace."""
    # Create dummy market data
    data = {
        "open": [2000.0] * 200,
        "high": [2005.0] * 200,
        "low": [1995.0] * 200,
        "close": [2000.0] * 200,
    }
    df = pd.DataFrame(data)

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )

    # We use UTC for the test to avoid deprecation warnings where possible
    decision = execution_filter.validate(
        signal=signal,
        market_data=df,
        current_drawdown=0.05
    )

    assert isinstance(decision, ExecutionDecision)
    assert "atr_volatility" in decision.trace
    assert "trend_angle" in decision.trace
    assert "ema_sequence" in decision.trace
    assert "momentum" in decision.trace
    assert "session_time" in decision.trace
    assert "drawdown_limit" in decision.trace
    assert "confidence_threshold" in decision.trace

    # All layers should have a 'passed' key
    for layer, result in decision.trace.items():
        assert "passed" in result, f"Layer {layer} missing 'passed' status"

def test_audit_log_execution_decision(audit_logger):
    """Verify that AuditLogger correctly records the execution trace."""
    trace = {
        "atr_volatility": {"passed": True, "ratio": 1.1},
        "drawdown_limit": {"passed": False, "current_drawdown": 0.2, "max_drawdown": 0.15}
    }

    entry_id = audit_logger.log_execution_decision(
        symbol="XAUUSD",
        direction=1,
        trace=trace,
        is_approved=False
    )

    with audit_logger.Session() as session:
        from sqlalchemy import select
        entry = session.execute(select(AuditEntry).where(AuditEntry.id == entry_id)).scalar_one_or_none()
        assert entry is not None
        assert entry.actor == "execution_filter"
        assert entry.metadata_json["symbol"] == "XAUUSD"
        assert entry.metadata_json["is_approved"] is False
        assert entry.metadata_json["trace"] == trace
