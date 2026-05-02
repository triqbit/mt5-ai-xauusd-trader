from datetime import datetime, timezone

import pandas as pd
import pytest

from src.analytics.journal_mining import (
    JournalMiner,
)


@pytest.fixture
def miner():
    return JournalMiner(db_url="sqlite:///:memory:")


@pytest.fixture
def sample_trades():
    return pd.DataFrame(
        [
            {
                "id": 1,
                "pnl": 100.0,
                "created_at": datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
                "algorithm": "ensemble",
            },
            {
                "id": 2,
                "pnl": -50.0,
                "created_at": datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc),
                "algorithm": "ensemble",
            },
            {
                "id": 3,
                "pnl": -20.0,
                "created_at": datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
                "algorithm": "ppo",
            },
            {
                "id": 4,
                "pnl": -30.0,
                "created_at": datetime(2024, 1, 1, 16, 0, tzinfo=timezone.utc),
                "algorithm": "ppo",
            },
            {
                "id": 5,
                "pnl": -10.0,
                "created_at": datetime(2024, 1, 1, 17, 0, tzinfo=timezone.utc),
                "algorithm": "ppo",
            },
        ]
    )


@pytest.fixture
def sample_signals():
    return pd.DataFrame(
        [
            {"id": 1, "volatility": 0.1, "confidence": 0.8, "pnl": 100.0, "algorithm": "ensemble"},
            {"id": 2, "volatility": 0.1, "confidence": 0.7, "pnl": -50.0, "algorithm": "ensemble"},
            {"id": 3, "volatility": 0.5, "confidence": 0.9, "pnl": -20.0, "algorithm": "ppo"},
            {"id": 4, "volatility": 0.5, "confidence": 0.85, "pnl": -30.0, "algorithm": "ppo"},
        ]
    )


def test_get_session(miner):
    # London session (08-17)
    dt_london = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    sessions = miner._get_session(dt_london)
    assert "London" in sessions

    # 02 UTC -> Sydney (22-07) and Tokyo (00-09)
    dt_early = datetime(2024, 1, 1, 2, 0, tzinfo=timezone.utc)
    sessions = miner._get_session(dt_early)
    assert "Sydney" in sessions
    assert "Tokyo" in sessions


def test_session_stats(miner, sample_trades):
    stats = miner.get_session_stats(sample_trades)
    assert len(stats) == 4
    london = next(s for s in stats if s.session_name == "London")
    assert london.trade_count > 0
    # 10, 11, 15, 16 are in London (8-17)
    assert london.trade_count == 4


def test_volatility_patterns(miner, sample_signals):
    patterns = miner.analyze_volatility_patterns(sample_signals)
    assert len(patterns) > 0
    # High volatility (0.5) has 2 signals, both losses -> 1.0 FP rate
    high_vol = next(p for p in patterns if p.volatility_bucket in ["High", "Extreme", "Standard"])
    assert high_vol.signal_count >= 2


def test_drawdown_clusters(miner, sample_trades):
    # Trades 2, 3, 4, 5 are consecutive losses in sample_trades
    # id 1: pnl 100
    # id 2: pnl -50
    # id 3: pnl -20
    # id 4: pnl -30
    # id 5: pnl -10
    clusters = miner.detect_drawdown_clusters(sample_trades)
    assert len(clusters) == 1
    assert clusters[0].trade_count == 4
    assert clusters[0].total_loss == -110.0


def test_profitable_patterns(miner, sample_trades):
    patterns = miner.find_profitable_patterns(sample_trades)
    # Ensemble: 1 win, 1 loss. Win rate 0.5. Profit factor 100/50 = 2.0
    ensemble = next(p for p in patterns if p.value == "ensemble")
    assert ensemble.win_rate == 0.5
    assert ensemble.profit_factor == 2.0


def test_risk_blocks(miner, sample_signals):
    risk_events = pd.DataFrame(
        [
            {"event_type": "MAX_DRAWDOWN", "signal_id": 1},
            {"event_type": "MAX_DRAWDOWN", "signal_id": 2},
            {"event_type": "SPREAD_TOO_WIDE", "signal_id": 3},
        ]
    )
    blocks = miner.analyze_risk_blocks(risk_events, sample_signals)
    assert len(blocks) == 2
    max_dd = next(b for b in blocks if b.reason == "MAX_DRAWDOWN")
    assert max_dd.count == 2
    assert "ensemble" in max_dd.impacted_algorithms


def test_run_mining(miner):
    # Setup database with some data
    with miner.Session() as session:
        from src.core.trade_logger import ModelSignal, RiskEvent, Trade

        sig = ModelSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            algorithm="ensemble",
            confidence=0.8,
            volatility=0.1,
        )
        session.add(sig)
        session.commit()

        trd = Trade(
            ticket=123,
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            lot_size=0.1,
            pnl=100.0,
            status="CLOSED",
            signal_id=sig.id,
        )
        session.add(trd)

        evt = RiskEvent(event_type="MAX_DRAWDOWN", signal_id=sig.id)
        session.add(evt)
        session.commit()

    report = miner.run_mining()
    assert isinstance(report.timestamp, datetime)
    assert len(report.session_analysis) == 4
    assert len(report.volatility_patterns) > 0
    assert len(report.profitable_concentrations) > 0
    assert len(report.risk_block_summary) == 1


def test_empty_dataframe_guards(miner):
    empty_df = pd.DataFrame()
    assert miner.get_session_stats(empty_df) == []
    assert miner.analyze_volatility_patterns(empty_df) == []
    assert miner.detect_drawdown_clusters(empty_df) == []
    assert miner.find_profitable_patterns(empty_df) == []
    assert miner.analyze_risk_blocks(empty_df, empty_df) == []


def test_volatility_patterns_no_volatility_col(miner):
    df = pd.DataFrame([{"id": 1, "pnl": 100}])
    assert miner.analyze_volatility_patterns(df) == []


def test_volatility_patterns_all_nan(miner):
    df = pd.DataFrame([{"id": 1, "volatility": None, "pnl": 100}])
    assert miner.analyze_volatility_patterns(df) == []


def test_drawdown_clusters_single_loss(miner):
    # Should not form a cluster (need 3+)
    df = pd.DataFrame([{"id": 1, "pnl": -10.0, "created_at": datetime.now(timezone.utc)}])
    assert miner.detect_drawdown_clusters(df) == []
