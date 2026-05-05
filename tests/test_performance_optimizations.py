
import pytest
from unittest.mock import MagicMock
from src.core.decision_support import DecisionSupportSystem, DecisionPacket
from src.core.trade_logger import TradeLogger
from src.core.constants import SignalDirection
import os

def test_decision_support_optimization():
    """Verify that format_for_operator returns early when console is provided."""
    dss = DecisionSupportSystem()
    mock_packet = MagicMock()
    mock_packet.is_executable = True
    mock_packet.direction = SignalDirection.BUY
    mock_packet.symbol = "XAUUSD"
    mock_packet.consensus = "Strong"
    mock_packet.blocking_reasons = []

    # Concrete values for attributes used in formatting in DSS
    mock_packet.regime.label.value = "Trending"
    mock_packet.regime.confidence = 0.85
    mock_packet.regime.volatility_index = 1.2
    mock_packet.regime.transition_score = 0.1

    mock_packet.performance.sharpe_ratio = 2.0
    mock_packet.performance.profit_factor = 1.5
    mock_packet.performance.recovery_factor = 1.2
    mock_packet.performance.win_rate = 0.6
    mock_packet.performance.win_loss_ratio = 1.1
    mock_packet.performance.total_trades = 100

    mock_packet.macro_risk.active_events = []
    mock_packet.macro_risk.is_blocked = False
    mock_packet.macro_risk.reason = "Clear"

    # Values for SignalExplainer formatting
    mock_packet.explanation.direction = SignalDirection.BUY
    mock_packet.explanation.symbol = "XAUUSD"
    mock_packet.explanation.total_confidence = 0.8
    mock_packet.explanation.human_readable_summary = "Signal is good"
    mock_packet.explanation.model_attributions = []
    mock_packet.explanation.feature_contributions = []
    mock_packet.explanation.execution_summary.filters = []
    mock_packet.explanation.risk_assessment.passed = True
    mock_packet.explanation.risk_assessment.risk_reward_ratio = 2.0
    mock_packet.explanation.risk_assessment.kelly_fraction = 0.05
    mock_packet.explanation.risk_assessment.rejection_reasons = []
    mock_packet.explanation.regime_context.regime_name = "Trending"
    mock_packet.explanation.regime_context.volatility_state = "Normal"
    mock_packet.explanation.regime_context.is_favorable = True

    mock_console = MagicMock()

    # This should return "" and print to mock_console
    result = dss.format_for_operator(mock_packet, console=mock_console)

    assert result == ""
    assert mock_console.print.called

def test_trade_logger_persistence_flag():
    """Verify that read_performance_report only persists when requested."""
    db_path = "test_perf_flag.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    logger = TradeLogger(db_url=f"sqlite:///{db_path}")
    from src.core.trade_logger import Base
    Base.metadata.create_all(logger.engine)

    # Need some trades to calculate metrics
    logger.log_trade(1, "XAUUSD", 1, 2000.0, 0.1)
    logger.update_trade(1, 2010.0, pnl=100.0)

    # Initially no metrics
    with logger.Session() as session:
        from src.core.trade_logger import PerformanceMetric
        count_before = session.query(PerformanceMetric).count()
        assert count_before == 0

    # Call without persist (default)
    logger.read_performance_report(persist=False)
    with logger.Session() as session:
        assert session.query(PerformanceMetric).count() == 0

    # Call with persist
    logger.read_performance_report(persist=True)
    with logger.Session() as session:
        assert session.query(PerformanceMetric).count() == 1

    if os.path.exists(db_path):
        os.remove(db_path)
