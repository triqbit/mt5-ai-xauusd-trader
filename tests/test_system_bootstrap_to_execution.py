"""
MT5 AI/ML Trading Bot - System Integration Test
tests/test_system_bootstrap_to_execution.py

Verifies the high-value system path:
Config Loading -> Component Bootstrap -> Health Gate -> Full Execution Iteration -> Audit Traceability
"""

import os
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import select

# We rely on conftest.py for initial mocks of talib, MetaTrader5, and telegram.
# We only add specific overrides here if needed.
from src.core.audit_log import AuditEntry, AuditLogger
from src.core.config import get_config
from src.core.constants import SignalDirection
from src.core.feature_engineering import FeatureEngineer
from src.core.health import ComponentStatus, HealthStatus, init_health_checker
from src.core.schemas import TradeSignal
from src.core.trade_logger import RiskEvent, Trade, TradeLogger
from src.models.base_model import Signal
from src.trading.audited_risk_manager import AuditedRiskManager
from src.trading.execution_filter import ExecutionFilter
from src.trading.mt5_connector import MT5Connector


@pytest.fixture
def system_env(tmp_path):
    """Sets up a temporary environment for system integration testing."""
    db_path = tmp_path / "system.db"
    audit_db_path = tmp_path / "audit.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    env_vars = {
        "MT5_LOGIN": "123456",
        "MT5_PASSWORD": "ValidPassword",
        "MT5_SERVER": "ValidServer",
        "MT5_PATH": "C:/Program Files/MetaTrader 5/terminal64.exe",
        "MODE": "demo",
        "SYMBOL": "XAUUSD",
        "TIMEFRAME": "M5",
        "DATABASE_URL": f"sqlite:///{db_path}",
        "LOGS_DIR": str(logs_dir),
        "RISK_PER_TRADE": "0.01",
        "MAX_DRAWDOWN": "0.15",
        "TELEGRAM_TOKEN": "123:abc",
        "TELEGRAM_CHAT_ID": "12345"
    }

    with patch.dict(os.environ, env_vars):
        get_config.cache_clear()
        cfg = get_config()

        # Initialize loggers
        # Note: AuditLogger is a singleton, we need to reset it for tests if it was already initialized
        AuditLogger._instance = None
        AuditLogger._initialized = False
        audit_logger = AuditLogger(db_url=f"sqlite:///{audit_db_path}")

        trade_logger = TradeLogger(db_url=f"sqlite:///{db_path}")

        yield cfg, audit_logger, trade_logger

def test_full_system_bootstrap_and_execution_audit(system_env):
    """
    Integration Path: Config -> Bootstrap -> Health -> Execution -> Audit
    Verifies that a successful trade flow is correctly recorded in all audit trails.
    """
    cfg, audit_logger, trade_logger = system_env

    # 0. Initial Audit (Simulate main.py)
    audit_logger.log_config_snapshot(cfg.model_dump(mode="json"))

    # 1. Setup MT5 Mocks
    import MetaTrader5 as mt5
    mt5.initialize.return_value = True
    mt5.login.return_value = True

    acc_info = MagicMock()
    acc_info.balance = 10000.0
    acc_info.equity = 10000.0
    acc_info.trade_allowed = True
    acc_info.get.side_effect = lambda k, d=None: {"trade_allowed": True, "balance": 10000.0}.get(k, d)
    mt5.account_info.return_value = acc_info

    term_info = MagicMock()
    term_info.trade_allowed = True
    term_info.get.side_effect = lambda k, d=None: {"algo_trading": True}.get(k, d)
    mt5.terminal_info.return_value = term_info

    n_bars = 500
    start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rates = np.zeros(n_bars, dtype=[('time', 'i8'), ('open', 'f8'), ('high', 'f8'), ('low', 'f8'), ('close', 'f8'), ('tick_volume', 'i8')])
    rates['close'] = np.linspace(2000, 2010, n_bars)
    rates['high'] = rates['close'] + 1
    rates['low'] = rates['close'] - 1
    rates['open'] = rates['close']
    rates['tick_volume'] = 100
    rates['time'] = [int((start_time + timedelta(minutes=5*i)).timestamp()) for i in range(n_bars)]
    mt5.copy_rates_from_pos.return_value = rates

    tick_info = MagicMock()
    tick_info.bid = 2010.0
    tick_info.ask = 2010.1
    tick_info.time = int(time.time())
    tick_info.get.side_effect = lambda k, d=None: {"bid": 2010.0, "ask": 2010.1}.get(k, d)
    mt5.symbol_info_tick.return_value = tick_info

    symbol_info = MagicMock()
    symbol_info.visible = True
    symbol_info.trade_mode = 0
    symbol_info.point = 0.01
    symbol_info.get.side_effect = lambda k, d=None: {"tradable": True}.get(k, d)
    mt5.symbol_info.return_value = symbol_info

    # 2. Bootstrap Components
    connector = MT5Connector(cfg)
    connector._is_initialized = True

    risk_manager = AuditedRiskManager(cfg, account_balance=10000.0, logger_db=trade_logger)
    execution_filter = ExecutionFilter(max_drawdown=cfg.max_drawdown, config=cfg)
    feature_engineer = FeatureEngineer(base_timeframe=cfg.timeframe, timeframes=["M15", "H1"])

    mock_model = MagicMock()
    mock_model.predict.return_value = Signal(
        direction=SignalDirection.BUY,
        confidence=0.85,
        metadata={"per_algo_votes": {"ppo": 1}, "weights": {"ppo": 1.0}}
    )

    # 3. Health Gate
    from src.core.health import HealthChecker
    with patch.object(HealthChecker, "check_config", return_value=ComponentStatus(status=HealthStatus.HEALTHY, message="OK")), \
         patch.object(HealthChecker, "check_redis", return_value=ComponentStatus(status=HealthStatus.HEALTHY, message="OK")), \
         patch.object(HealthChecker, "check_mt5", return_value=ComponentStatus(status=HealthStatus.HEALTHY, message="OK")), \
         patch.object(HealthChecker, "check_system_resources", return_value=ComponentStatus(status=HealthStatus.HEALTHY, message="OK")), \
         patch.object(HealthChecker, "check_disk_space", return_value=ComponentStatus(status=HealthStatus.HEALTHY, message="OK")):

            health_checker = init_health_checker(cfg, connector, trade_logger, mock_model, audit_logger=audit_logger)
            report = health_checker.startup_gate()
            assert report.status == HealthStatus.HEALTHY

    # 4. Simulated Execution Cycle
    df_raw = connector.get_ohlcv(cfg.symbol, cfg.timeframe, n_bars=n_bars)
    tick = connector.get_tick(cfg.symbol)
    df_raw.index = pd.to_datetime(df_raw["time"], unit="s")
    df_raw = df_raw.drop(columns=["time"])

    df_features = feature_engineer.compute_features(df_raw)
    df_features = df_features.astype(np.float64)
    df_features["base_M5_ema_21"] = np.linspace(2000, 2010, len(df_features))
    df_features["base_M5_ema_8"] = df_features["base_M5_ema_21"] + 5
    df_features["base_M5_ema_50"] = df_features["base_M5_ema_21"] - 5
    df_features["base_M5_ema_200"] = df_features["base_M5_ema_21"] - 10
    df_features["base_M5_rsi"] = 60.0
    df_features["base_M5_atr"] = 1.0

    obs = df_features.values[-1]
    signal_obj = mock_model.predict(obs)

    audit_logger.log_prediction(
        symbol=cfg.symbol,
        direction=signal_obj.direction.value,
        confidence=signal_obj.confidence,
        model_metadata=signal_obj.metadata
    )

    price = tick["ask"] if signal_obj.direction == SignalDirection.BUY else tick["bid"]
    signal = TradeSignal(
        symbol=cfg.symbol,
        direction=signal_obj.direction.value,
        entry_price=price,
        stop_loss=price - 10.0,
        take_profit=price + 20.0,
        lot_size=0.1,
        algorithm="test",
        confidence=signal_obj.confidence
    )

    risk_approved = risk_manager.approve(signal)
    assert risk_approved is True

    drawdown = (risk_manager.peak_equity - risk_manager.balance) / risk_manager.peak_equity
    # Use a fixed Wednesday timestamp to avoid SESSION_CLOSED during CI runs on weekends
    fixed_timestamp = datetime(2024, 5, 22, 12, 0, tzinfo=timezone.utc)
    filter_decision = execution_filter.validate(
        signal,
        df_features,
        current_drawdown=drawdown,
        timestamp=fixed_timestamp
    )
    assert filter_decision.is_approved is True

    audit_logger.log_execution_decision(
        symbol=cfg.symbol,
        direction=signal.direction,
        trace=filter_decision.trace,
        is_approved=filter_decision.is_approved
    )

    res = MagicMock()
    res.retcode = 10009
    res.order = 123456
    res.comment = "Done"
    mt5.order_send.return_value = res
    mt5.TRADE_RETCODE_DONE = 10009

    ticket = connector.place_order(signal)
    assert ticket == 123456

    trade_logger.log_trade(
        ticket=ticket,
        symbol=cfg.symbol,
        direction=signal.direction,
        entry_price=price,
        lot_size=signal.lot_size
    )

    # 5. Verification
    with audit_logger.Session() as session:
        snapshot = session.execute(select(AuditEntry).where(AuditEntry.action == "config_snapshot")).scalars().first()
        assert snapshot is not None

        pred = session.execute(select(AuditEntry).where(AuditEntry.action == "prediction")).scalars().first()
        assert pred is not None

        risk_audit = session.execute(select(AuditEntry).where(AuditEntry.actor == "risk_engine")).scalars().first()
        assert risk_audit is not None
        assert risk_audit.metadata_json["passed"] is True

        exec_audit = session.execute(select(AuditEntry).where(AuditEntry.actor == "execution_filter")).scalars().first()
        assert exec_audit is not None
        assert exec_audit.metadata_json["is_approved"] is True

    with trade_logger.Session() as session:
        trade_record = session.execute(select(Trade).where(Trade.ticket == 123456)).scalars().first()
        assert trade_record is not None
        assert trade_record.status == "OPEN"

def test_system_failure_handling_risk_rejection(system_env):
    """
    Verifies that system-level risk rejection (e.g. drawdown limit)
    is correctly handled and logged across component boundaries.
    """
    cfg, audit_logger, trade_logger = system_env

    # 1. Setup Environment in Drawdown
    risk_manager = AuditedRiskManager(cfg, account_balance=10000.0, logger_db=trade_logger)
    # Simulate 20% drawdown (limit is 15%)
    risk_manager.update_equity(10000.0) # Peak
    risk_manager.update_equity(8000.0)  # Current

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.9
    )

    # 2. Execute Risk Approval - Should fail
    risk_approved = risk_manager.approve(signal)
    assert risk_approved is False

    # 3. Verify failure trace in Audit Log
    with audit_logger.Session() as session:
        # Check risk decision entry
        entry = session.execute(
            select(AuditEntry).where(AuditEntry.actor == "risk_engine", AuditEntry.action == "risk_decision")
        ).scalars().first()
        assert entry is not None
        assert entry.metadata_json["passed"] is False
        assert entry.metadata_json["decision_chain"]["circuit_breaker"] is False

        # Check operator action log for high-severity event
        halt_event = session.execute(
            select(AuditEntry).where(AuditEntry.action == "operator_circuit_breaker_triggered")
        ).scalars().first()
        assert halt_event is not None
        assert "drawdown limit hit" in halt_event.metadata_json["reason"].lower()

    # 4. Verify failure in Trade Log
    with trade_logger.Session() as session:
        risk_event = session.execute(
            select(RiskEvent).where(RiskEvent.event_type == "SIGNAL_REJECTED")
        ).scalars().first()
        assert risk_event is not None
        # Check if either 'circuit_breaker' or 'circuit breaker' is in description
        desc = risk_event.description.lower()
        assert "circuit_breaker" in desc or "circuit breaker" in desc
