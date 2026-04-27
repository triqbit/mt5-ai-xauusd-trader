"""
Unit tests for JournalMiner.
"""

import pytest
from datetime import datetime, timezone, timedelta
from src.core.trade_logger import TradeLogger, ModelSignal, Trade, RiskEvent
from src.analytics.journal_mining import JournalMiner

@pytest.fixture
def logger_db():
    # Use in-memory SQLite for testing
    return TradeLogger("sqlite:///:memory:")

@pytest.fixture
def populated_miner(logger_db):
    with logger_db.Session() as session:
        # Create some signals and trades
        for i in range(10):
            ts = datetime(2024, 5, 1, 10, 0, 0, tzinfo=timezone.utc) + timedelta(hours=i)
            sig = ModelSignal(
                symbol="XAUUSD",
                direction=1,
                entry_price=2300.0 + i,
                stop_loss=2295.0 + i,
                algorithm="ppo",
                timestamp=ts
            )
            session.add(sig)
            session.flush()

            trade = Trade(
                ticket=100 + i,
                symbol="XAUUSD",
                direction=1,
                entry_price=2300.0 + i,
                exit_price=2305.0 + i if i % 2 == 0 else 2290.0 + i,
                lot_size=0.1,
                pnl=500.0 if i % 2 == 0 else -1000.0,
                status="CLOSED",
                signal_id=sig.id
            )
            session.add(trade)

        # Add a drawdown cluster (3+ losses)
        for i in range(10, 13):
            ts = datetime(2024, 5, 2, 10, 0, 0, tzinfo=timezone.utc) + timedelta(hours=i)
            sig = ModelSignal(
                symbol="XAUUSD",
                direction=1,
                entry_price=2300.0,
                stop_loss=2290.0,
                algorithm="ppo",
                timestamp=ts
            )
            session.add(sig)
            session.flush()

            trade = Trade(
                ticket=200 + i,
                symbol="XAUUSD",
                direction=1,
                entry_price=2300.0,
                exit_price=2290.0,
                lot_size=0.1,
                pnl=-1000.0,
                status="CLOSED",
                signal_id=sig.id
            )
            session.add(trade)

        # Add some rejections
        for i in range(5):
            rej = RiskEvent(
                event_type="SIGNAL_REJECTED",
                description="Daily loss limit reached",
                symbol="XAUUSD",
                created_at=datetime.now(timezone.utc)
            )
            session.add(rej)

        session.commit()

    return JournalMiner(logger_db)

def test_analyze_sessions(populated_miner):
    report = populated_miner.run_full_analysis()
    assert len(report.session_analysis) > 0
    # Check if hour 10 is present (we started at 10:00)
    hours = [s.hour for s in report.session_analysis]
    assert 10 in hours

def test_analyze_volatility_patterns(populated_miner):
    report = populated_miner.run_full_analysis()
    assert len(report.volatility_patterns) > 0
    # In our fixture, we have SL distances of 5 (2300 - 2295) and 10 (2300 - 2290)
    # Med Vol is < 5.0 (actually we used 5.0 as limit for High Vol in code)
    # Let's check names
    names = [v.regime_name for v in report.volatility_patterns]
    assert any(n in ["Med Vol", "High Vol"] for n in names)

def test_analyze_drawdown_clusters(populated_miner):
    report = populated_miner.run_full_analysis()
    assert len(report.drawdown_clusters) >= 1
    cluster = report.drawdown_clusters[0]
    assert cluster.trade_count >= 3
    assert cluster.total_loss < 0

def test_analyze_rejections(populated_miner):
    report = populated_miner.run_full_analysis()
    assert len(report.rejection_summary) == 1
    assert report.rejection_summary[0].reason == "Daily loss limit reached"
    assert report.rejection_summary[0].count == 5

def test_generate_recommendations(populated_miner):
    report = populated_miner.run_full_analysis()
    assert len(report.recommendations) > 0
    # Should include drawdown cluster recommendation
    assert any("drawdown clusters" in r for r in report.recommendations)
