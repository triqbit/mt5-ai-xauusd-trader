
import pytest
from datetime import datetime, timezone, time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.core.trade_logger import Base, ModelSignal, Trade, RiskEvent
from src.analytics.journal_mining import JournalMiner, TradingSession, VolatilityCondition

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def miner(db_session):
    miner = JournalMiner(db_url="sqlite:///:memory:")
    return miner

def test_get_sessions(miner):
    # Asian: 02:00 UTC
    dt_asian = datetime(2024, 1, 1, 2, 0, tzinfo=timezone.utc)
    sessions = miner._get_sessions(dt_asian)
    assert TradingSession.ASIAN in sessions

    # London & New York Overlap: 14:00 UTC
    dt_overlap = datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc)
    sessions = miner._get_sessions(dt_overlap)
    assert TradingSession.LONDON in sessions
    assert TradingSession.NEW_YORK in sessions

def test_analyze_sessions(miner, db_session):
    t1 = Trade(pnl=100.0, symbol="XAUUSD", direction=1, entry_price=2000.0, lot_size=0.1)
    t1.created_at = datetime(2024, 1, 1, 2, 0, tzinfo=timezone.utc)

    t2 = Trade(pnl=-50.0, symbol="XAUUSD", direction=-1, entry_price=2010.0, lot_size=0.1)
    t2.created_at = datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc)

    db_session.add(t1)
    db_session.add(t2)
    db_session.commit()

    # Reload from DB to ensure SQLAlchemy state is correct
    trades = db_session.query(Trade).all()
    stats = miner.analyze_sessions(trades)

    assert len(stats) > 0
    asian_stats = next((s for s in stats if s.session == TradingSession.ASIAN), None)
    assert asian_stats is not None
    assert asian_stats.trade_count == 1
    assert asian_stats.total_pnl == 100.0

    london_stats = next((s for s in stats if s.session == TradingSession.LONDON), None)
    assert london_stats is not None
    assert london_stats.trade_count == 1
    assert london_stats.total_pnl == -50.0

def test_analyze_volatility(miner, db_session):
    s1 = ModelSignal(symbol="XAUUSD", direction=1, entry_price=2000.0, stop_loss=1999.5, confidence=0.8) # Vol = 0.25 (LOW)
    t1 = Trade(symbol="XAUUSD", direction=1, entry_price=2000.0, lot_size=0.1, status="CLOSED", pnl=50.0)
    s1.trade = t1

    s2 = ModelSignal(symbol="XAUUSD", direction=-1, entry_price=2000.0, stop_loss=1995.0, confidence=0.7) # Vol = 2.5 (MEDIUM)
    t2 = Trade(symbol="XAUUSD", direction=-1, entry_price=2000.0, lot_size=0.1, status="CLOSED", pnl=-10.0)
    s2.trade = t2

    db_session.add(s1)
    db_session.add(s2)
    db_session.commit()

    signals = db_session.query(ModelSignal).all()
    analysis = miner.analyze_volatility(signals)

    assert len(analysis) > 0
    low_vol = next((a for a in analysis if a.condition == VolatilityCondition.LOW), None)
    assert low_vol is not None
    assert low_vol.signal_count == 1
    assert low_vol.false_positive_rate == 0.0 # It was a win

    med_vol = next((a for a in analysis if a.condition == VolatilityCondition.MEDIUM), None)
    assert med_vol is not None
    assert med_vol.signal_count == 1
    assert med_vol.false_positive_rate == 1.0 # It was a loss

def test_drawdown_clusters(miner):
    t1 = Trade(pnl=-10.0)
    t1.created_at = datetime(2024, 1, 1, 1, 0)
    t2 = Trade(pnl=-10.0)
    t2.created_at = datetime(2024, 1, 1, 2, 0)
    t3 = Trade(pnl=-10.0)
    t3.created_at = datetime(2024, 1, 1, 3, 0)
    t4 = Trade(pnl=50.0)
    t4.created_at = datetime(2024, 1, 1, 4, 0)
    t5 = Trade(pnl=-5.0)
    t5.created_at = datetime(2024, 1, 1, 5, 0)

    trades = [t1, t2, t3, t4, t5]

    clusters = miner._detect_drawdown_clusters(trades)
    assert len(clusters) == 1
    assert clusters[0].size == 3
    assert clusters[0].total_loss == -30.0

def test_analyze_block_reasons(miner):
    events = [
        RiskEvent(event_type="MAX_DRAWDOWN"),
        RiskEvent(event_type="MAX_DRAWDOWN"),
        RiskEvent(event_type="DAILY_LOSS_LIMIT"),
    ]

    stats = miner._analyze_block_reasons(events)
    assert len(stats) == 2
    dd_stats = next(s for s in stats if s.reason == "MAX_DRAWDOWN")
    assert dd_stats.count == 2
