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
    # Add symbol to sample_trades for this test
    df = sample_trades.copy()
    df["symbol"] = "XAUUSD"

    patterns = miner.find_profitable_patterns(df)
    # Ensemble: 1 win, 1 loss. Win rate 0.5. Profit factor 100/50 = 2.0
    ensemble = next(p for p in patterns if p.value == "ensemble")
    assert ensemble.win_rate == 0.5
    assert ensemble.profit_factor == 2.0

    # Symbol concentration
    xau = next(p for p in patterns if p.value == "XAUUSD")
    assert xau.attribute == "symbol"
    assert xau.total_trades == 5

    # Day of week analysis (2024-01-01 was a Monday)
    monday = next(p for p in patterns if p.value == "Monday")
    assert monday.attribute == "day"
    assert monday.total_trades == 5


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
            exit_price=2100.0,
            lot_size=0.1,
            pnl=100.0,
            status="CLOSED",
            signal_id=sig.id,
        )
        # Manually set updated_at to simulate duration (10 mins)
        trd.created_at = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        trd.updated_at = datetime(2024, 1, 1, 12, 10, tzinfo=timezone.utc)
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
    assert report.avg_win_duration == 10.0


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


def test_find_frequent_motifs(miner):
    signals = pd.DataFrame(
        [
            {
                "id": 1,
                "algorithm": "ensemble",
                "direction": 1,
                "volatility": 0.05,
                "confidence": 0.85,
                "pnl": -10,
                "win": False,
                "created_at": datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc),
            },
            {
                "id": 2,
                "algorithm": "ensemble",
                "direction": 1,
                "volatility": 0.05,
                "confidence": 0.85,
                "pnl": -20,
                "win": False,
                "created_at": datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
            },
            {
                "id": 3,
                "algorithm": "ppo",
                "direction": -1,
                "volatility": 0.5,
                "confidence": 0.95,
                "pnl": 100,
                "win": True,
                "created_at": datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            },
            {
                "id": 4,
                "algorithm": "ppo",
                "direction": -1,
                "volatility": 0.5,
                "confidence": 0.95,
                "pnl": 50,
                "win": True,
                "created_at": datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc),
            },
        ]
    )
    motifs = miner.find_frequent_motifs(signals)
    assert len(motifs) == 2
    # Ensemble motif (direction 1, Low vol, High conf) has 0% win rate
    ensemble_motif = next(m for m in motifs if m.algorithm == "ensemble")
    assert ensemble_motif.win_rate == 0.0
    assert ensemble_motif.volatility_bucket == "Low"
    assert ensemble_motif.confidence_bucket == "High"
    assert ensemble_motif.session in ["London", "New York"]


def test_strategy_state_correlation(miner):
    # Setup trades with a drawdown cluster
    now = datetime.now(timezone.utc)
    trades = pd.DataFrame(
        [
            {"id": 1, "pnl": -10, "created_at": now, "signal_id": 1},
            {"id": 2, "pnl": -10, "created_at": now + pd.Timedelta(minutes=1), "signal_id": 2},
            {"id": 3, "pnl": -10, "created_at": now + pd.Timedelta(minutes=2), "signal_id": 3},
        ]
    )

    # Risk events: one within 24h of the cluster, one outside
    risk_events = pd.DataFrame(
        [
            {"event_type": "MAX_DRAWDOWN", "created_at": now + pd.Timedelta(hours=1)},
            {"event_type": "MAX_DRAWDOWN", "created_at": now + pd.Timedelta(hours=48)},
        ]
    )

    correlations = miner.analyze_strategy_state_correlation(risk_events, trades)
    # 1 out of 2 events are in 'weak state' (within 24h of cluster)
    assert correlations["MAX_DRAWDOWN"] == 0.5


def test_to_report_section_with_toxic_motif(miner):
    from src.analytics.journal_mining import BlockReasonSummary, JournalReport, SignalMotif

    report = JournalReport(
        session_analysis=[],
        volatility_patterns=[],
        drawdown_clusters=[],
        profitable_concentrations=[],
        risk_block_summary=[
            BlockReasonSummary(
                reason="FRAGILE", count=10, impacted_algorithms=["ppo"], weak_state_correlation=0.9
            )
        ],
        recurring_motifs=[
            SignalMotif(
                algorithm="ensemble",
                direction=1,
                volatility_bucket="High",
                confidence_bucket="Medium",
                session="London",
                frequency=5,
                win_rate=0.1,
            )
        ],
        avg_win_duration=15.5,
        avg_loss_duration=45.2,
    )

    section = report.to_report_section()
    # Should detect Strategy Fragility and Toxic Motif
    risk_types = [r.type for r in section.behavioral_risks]
    assert "Strategy Fragility" in risk_types
    assert "Toxic Motif" in risk_types
    assert section.avg_win_duration == 15.5
    assert section.avg_loss_duration == 45.2
    assert section.motifs[0].session == "London"


def test_analyze_trade_durations(miner):
    from src.core.trade_logger import Trade

    now = datetime.now(timezone.utc)
    trades = [
        Trade(
            pnl=100,
            created_at=now,
            updated_at=now + pd.Timedelta(minutes=10),
            status="CLOSED",
            exit_price=2000,
        ),
        Trade(
            pnl=-50,
            created_at=now,
            updated_at=now + pd.Timedelta(minutes=30),
            status="CLOSED",
            exit_price=1990,
        ),
    ]

    durations = miner.analyze_trade_durations(trades)
    assert durations["avg_win_duration"] == 10.0
    assert durations["avg_loss_duration"] == 30.0


def test_detect_pre_drawdown_motifs(miner):
    now = datetime.now(timezone.utc)
    # 3 consecutive losses form a cluster starting at now
    trades = pd.DataFrame(
        [
            {"id": 1, "pnl": -10, "created_at": now, "signal_id": 1},
            {"id": 2, "pnl": -10, "created_at": now + pd.Timedelta(minutes=1), "signal_id": 2},
            {"id": 3, "pnl": -10, "created_at": now + pd.Timedelta(minutes=2), "signal_id": 3},
        ]
    )

    # Signal 1 hour before cluster
    signals = pd.DataFrame(
        [
            {
                "id": 10,
                "algorithm": "ensemble",
                "direction": 1,
                "volatility": 0.1,
                "confidence": 0.8,
                "pnl": -5,
                "created_at": now - pd.Timedelta(hours=1),
            },
            {
                "id": 11,
                "algorithm": "ensemble",
                "direction": 1,
                "volatility": 0.1,
                "confidence": 0.8,
                "pnl": -5,
                "created_at": now - pd.Timedelta(hours=1, minutes=1),
            },
        ]
    )

    motifs = miner.detect_pre_drawdown_motifs(signals, trades)
    assert len(motifs) == 1
    assert motifs[0].algorithm == "ensemble"
    assert motifs[0].frequency == 2


def test_find_frequent_motifs_with_clusters(miner):
    now = datetime.now(timezone.utc)
    trades = pd.DataFrame(
        [
            {"id": 1, "pnl": -10, "created_at": now, "signal_id": 1},
            {"id": 2, "pnl": -10, "created_at": now + pd.Timedelta(minutes=1), "signal_id": 2},
            {"id": 3, "pnl": -10, "created_at": now + pd.Timedelta(minutes=2), "signal_id": 3},
        ]
    )

    signals = pd.DataFrame(
        [
            {
                "id": 1,
                "algorithm": "ensemble",
                "direction": 1,
                "volatility": 0.1,
                "confidence": 0.8,
                "pnl": -10,
                "created_at": now,
            },
            {
                "id": 2,
                "algorithm": "ensemble",
                "direction": 1,
                "volatility": 0.1,
                "confidence": 0.8,
                "pnl": -10,
                "created_at": now + pd.Timedelta(minutes=1),
            },
        ]
    )

    motifs = miner.find_frequent_motifs(signals, trades)
    assert len(motifs) == 1
    assert motifs[0].cluster_frequency == 2


def test_profitable_patterns_multi_attribute(miner, sample_trades):
    # Add symbol and algorithm to sample_trades
    df = sample_trades.copy()
    df["symbol"] = "XAUUSD"
    # sessions will be added by run_mining or manually for testing find_profitable_patterns
    df["sessions"] = df["created_at"].apply(miner._get_session)

    patterns = miner.find_profitable_patterns(df)

    # Check for algo_session attribute
    algo_sess = [p for p in patterns if p.attribute == "algo_session"]
    assert len(algo_sess) > 0
    # ensemble @ London (10, 11) -> 2 trades
    ensemble_london = next(p for p in algo_sess if p.value == "ensemble @ London")
    assert ensemble_london.total_trades == 2


def test_toxic_motif_sorting(miner):
    # Motif A: 10% win rate, 10 trades
    # Motif B: 0% win rate, 2 trades
    signals = pd.DataFrame(
        [
            {
                "id": i,
                "algorithm": "A",
                "direction": 1,
                "volatility": 0.1,
                "confidence": 0.8,
                "pnl": -1,
                "win": False,
                "created_at": datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            }
            for i in range(10)
        ]
    )
    # Give Motif A some wins to make WR 10%
    signals.loc[0, "win"] = True

    signals_b = pd.DataFrame(
        [
            {
                "id": i + 10,
                "algorithm": "B",
                "direction": 1,
                "volatility": 0.1,
                "confidence": 0.8,
                "pnl": -1,
                "win": False,
                "created_at": datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            }
            for i in range(2)
        ]
    )

    all_signals = pd.concat([signals, signals_b])
    motifs = miner.find_frequent_motifs(all_signals)

    # Motif A toxic score: (1-0.1) * log(11) = 0.9 * 2.39 = 2.15
    # Motif B toxic score: (1-0) * log(3) = 1 * 1.09 = 1.09
    # A should be first because it has higher frequency and still low win rate
    assert motifs[0].algorithm == "A"
