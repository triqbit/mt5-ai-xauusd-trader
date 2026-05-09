"""
MT5 AI/ML Trading Bot - Enterprise Integration Test
tests/test_backtest_auditing.py

Verifies that backtesting events are correctly captured by the AuditLogger.
"""

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import pytest
from src.core.audit_log import AuditLogger, AuditEntry
from src.core.database import DatabaseManager, Base, get_db_manager
from src.trading.backtester import BacktestEngine
from src.core.schemas import TradeSignal
from src.core.constants import SignalDirection
from sqlalchemy import select

@pytest.fixture
def mock_feature_engineer():
    fe = type('MockFE', (), {})()
    fe.compute_features = lambda df, **kwargs: df
    fe.base_timeframe = "M5"
    fe.normalize = False
    return fe

@pytest.fixture
def mock_execution_filter():
    ef = type('MockEF', (), {})()
    ef.validate = lambda signal, df, **kwargs: type('EFDecision', (), {
        'is_approved': True,
        'blocked_by': None,
        'trace': {}
    })()
    return ef

@pytest.fixture
def mock_model():
    model = type('MockModel', (), {})()
    model.predict = lambda obs, **kwargs: TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY.value,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="mock",
        confidence=0.9
    )
    return model

def test_backtest_auditing_integration(tmp_path, mock_feature_engineer, mock_execution_filter, mock_model):
    """
    Verifies that running a backtest records auditing events in the database.
    """
    audit_db_file = tmp_path / "audit.db"
    audit_db_url = f"sqlite:///{audit_db_file}"

    # Initialize DatabaseManager first
    if DatabaseManager._instance:
        DatabaseManager._instance._initialized = False
    DatabaseManager(db_url=audit_db_url)
    Base.metadata.create_all(DatabaseManager.get_instance().engine)

    # Initialize AuditLogger singleton for this test
    AuditLogger._instance = None
    AuditLogger._initialized = False
    AuditLogger()

    # Create dummy OHLCV data
    dates = pd.date_range(start="2024-01-01", periods=100, freq="5min")
    df_raw = pd.DataFrame({
        "open": np.linspace(2000, 2010, 100),
        "high": np.linspace(2005, 2015, 100),
        "low": np.linspace(1995, 2005, 100),
        "close": np.linspace(2000, 2010, 100),
        "tick_volume": [100] * 100
    }, index=dates)

    engine = BacktestEngine(
        symbol="XAUUSD",
        initial_balance=10000.0,
        feature_engineer=mock_feature_engineer,
        execution_filter=mock_execution_filter
    )

    # Run a small walk-forward step
    engine.run_walk_forward(
        df_raw,
        mock_model,
        train_window=50,
        test_window=20,
        step_size=20
    )

    # Verify that audit entries were recorded
    with get_db_manager().get_session() as session:
        entries = session.execute(select(AuditEntry).where(AuditEntry.actor == "system", AuditEntry.action == "backtest_started")).scalars().all()
        assert len(entries) > 0
        assert entries[0].action == "backtest_started"
