"""
Unit tests for JournalMiner.
"""

import os
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.analytics.journal_mining import JournalMiner
from src.core.trade_logger import Base, ModelSignal, RiskEvent, Trade


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_analyze_sessions(session):
    # Add trades for different sessions
    # London (8-13), NY (17-22), Asia (else)
    now = datetime.now(timezone.utc)
    t1 = Trade(
        ticket=1, symbol="XAUUSD", direction=1, entry_price=2000, lot_size=0.1, pnl=100, status="CLOSED"
    )
    t1.created_at = now.replace(hour=10)  # London

    t2 = Trade(
        ticket=2, symbol="XAUUSD", direction=-1, entry_price=2000, lot_size=0.1, pnl=-50, status="CLOSED"
    )
    t2.created_at = now.replace(hour=19)  # NY

    session.add_all([t1, t2])
    session.commit()

    miner = JournalMiner(session)
    results = miner.analyze_sessions()

    assert len(results) >= 2
    london = next(s for s in results if s.session_name == "London")
    ny = next(s for s in results if s.session_name == "New York")

    assert london.trade_count == 1
    assert london.total_pnl == 100
    assert ny.total_pnl == -50


def test_analyze_volatility_patterns(session):
    # Add signals with volatility and corresponding trades
    s1 = ModelSignal(symbol="XAUUSD", direction=1, entry_price=2000, volatility=0.5, algorithm="ppo")
    s2 = ModelSignal(symbol="XAUUSD", direction=-1, entry_price=2000, volatility=2.0, algorithm="ppo")
    s3 = ModelSignal(symbol="XAUUSD", direction=1, entry_price=2000, volatility=5.0, algorithm="ppo")
    session.add_all([s1, s2, s3])
    session.commit()

    t1 = Trade(ticket=1, symbol="XAUUSD", direction=1, entry_price=2000, lot_size=0.1, pnl=100, status="CLOSED", signal_id=s1.id)
    t2 = Trade(ticket=2, symbol="XAUUSD", direction=-1, entry_price=2000, lot_size=0.1, pnl=100, status="CLOSED", signal_id=s2.id)
    t3 = Trade(ticket=3, symbol="XAUUSD", direction=1, entry_price=2000, lot_size=0.1, pnl=-50, status="CLOSED", signal_id=s3.id)
    session.add_all([t1, t2, t3])
    session.commit()

    miner = JournalMiner(session)
    results = miner.analyze_volatility_patterns()

    assert len(results) == 3  # Low, Medium, High because of qcut(3)
    # Volatilities: 0.5, 2.0, 5.0 -> Low: 0.5, Medium: 2.0, High: 5.0
    high_vol = next(v for v in results if v.volatility_bucket == "High")
    assert high_vol.trade_count == 1
    assert high_vol.avg_pnl == -50


def test_analyze_drawdown_clusters(session):
    # 3+ losses in a row
    now = datetime.now(timezone.utc)
    s1 = ModelSignal(symbol="XAUUSD", direction=1, entry_price=2000, algorithm="ppo")
    session.add(s1)
    session.commit()

    trades = []
    for i in range(4):
        t = Trade(ticket=i, symbol="XAUUSD", direction=1, entry_price=2000, lot_size=0.1, pnl=-10, status="CLOSED", signal_id=s1.id)
        t.created_at = now + timedelta(minutes=i)
        trades.append(t)

    session.add_all(trades)
    session.commit()

    miner = JournalMiner(session)
    clusters = miner.analyze_drawdown_clusters()

    assert len(clusters) == 1
    assert clusters[0].trade_count == 4
    assert clusters[0].total_loss == -40
    assert "ppo" in clusters[0].common_algorithms


def test_analyze_rejections(session):
    r1 = RiskEvent(event_type="SIGNAL_REJECTED", description="Confidence too low", symbol="XAUUSD")
    r2 = RiskEvent(event_type="SIGNAL_REJECTED", description="Confidence too low", symbol="XAUUSD")
    r3 = RiskEvent(event_type="SIGNAL_REJECTED", description="Daily loss limit", symbol="XAUUSD")

    session.add_all([r1, r2, r3])
    session.commit()

    miner = JournalMiner(session)
    rejections = miner.analyze_rejections()

    assert len(rejections) == 2
    assert rejections[0].reason == "Confidence too low"
    assert rejections[0].count == 2
    assert rejections[1].reason == "Daily loss limit"
    assert rejections[1].count == 1


def test_generate_report(session):
    # Just ensure it runs without error and returns a JournalReport
    miner = JournalMiner(session)
    report = miner.generate_report()
    assert isinstance(report.summary, str)
    assert len(report.sessions) == 0  # No trades added
