import uuid
from datetime import datetime, timezone

import pandas as pd
import pytest

from src.analytics.journal_mining import (
    JournalMiner,
)


@pytest.fixture
def miner():
    # Use a unique URI to ensure database isolation between tests despite LRU caching of engines
    unique_id = uuid.uuid4().hex
    return JournalMiner(db_url=f"sqlite:///file:{unique_id}?mode=memory&cache=shared")


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
    # Cumulative losses: -50, -70, -100, -110. Max drop should be 110.
    assert clusters[0].max_equity_drop == 110.0


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
    assert ensemble_motif.is_toxic is True
    assert ensemble_motif.is_golden is False
    assert ensemble_motif.volatility_bucket == "Low"
    assert ensemble_motif.confidence_bucket == "High"
    assert ensemble_motif.session in ["London", "New York"]

    # PPO motif has 100% win rate
    ppo_motif = next(m for m in motifs if m.algorithm == "ppo")
    assert ppo_motif.win_rate == 1.0
    assert ppo_motif.is_toxic is False
    assert ppo_motif.is_golden is True


def test_strategy_state_correlation(miner):
    # Setup trades with a drawdown cluster
    now = datetime.now(timezone.utc)
    trades = pd.DataFrame(
        [
            {"id": 1, "pnl": -10, "created_at": now, "signal_id": 1},
            {"id": 2, "pnl": -10, "created_at": now + pd.Timedelta(minutes=1), "signal_id": 2},
            {"id": 3, "pnl": -10, "created_at": now + pd.Timedelta(minutes=2), "signal_id": 3},
            {"id": 9, "pnl": 10, "created_at": now + pd.Timedelta(minutes=3), "signal_id": 9},
        ]
    )

    # Risk events: one within 24h BEFORE, one DURING, one outside
    risk_events = pd.DataFrame(
        [
            {"event_type": "MAX_DRAWDOWN", "created_at": now - pd.Timedelta(hours=1)},
            {"event_type": "MAX_DRAWDOWN", "created_at": now + pd.Timedelta(minutes=1)},
            {"event_type": "MAX_DRAWDOWN", "created_at": now - pd.Timedelta(hours=48)},
        ]
    )

    correlations = miner.analyze_strategy_state_correlation(risk_events, trades)
    # 2 out of 3 events are in 'weak state' (preceding or during cluster)
    assert round(correlations["MAX_DRAWDOWN"], 2) == 0.67


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
                is_toxic=True,
                expectancy=-10,
            ),
            SignalMotif(
                algorithm="ppo",
                direction=1,
                volatility_bucket="Low",
                confidence_bucket="High",
                session="New York",
                frequency=5,
                win_rate=0.9,
                is_golden=True,
                expectancy=50,
            ),
        ],
        avg_win_duration=15.5,
        avg_loss_duration=45.2,
    )

    section = report.to_report_section()
    # Should detect Strategy Fragility, Toxic Motif and Golden Motif
    risk_types = [r.type for r in section.behavioral_risks]
    assert "Strategy Fragility" in risk_types
    assert "Toxic Motif" in risk_types
    assert "Golden Motif" in risk_types
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


def test_find_combination_motifs(miner):
    # Use fixed timestamps to avoid session jitter
    base_time = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)

    # Toxic Instance 1 (10:00)
    t1 = base_time
    trades_toxic1 = pd.DataFrame(
        [
            {"id": 1, "pnl": -10, "created_at": t1, "signal_id": 1},
            {"id": 2, "pnl": -10, "created_at": t1 + pd.Timedelta(minutes=1), "signal_id": 2},
            {"id": 3, "pnl": -10, "created_at": t1 + pd.Timedelta(minutes=2), "signal_id": 3},
            {
                "id": 4,
                "pnl": 10,
                "created_at": t1 + pd.Timedelta(minutes=3),
                "signal_id": 4,
            },  # Win Breaker
            {
                "id": 41,
                "pnl": -10,
                "created_at": t1 + pd.Timedelta(minutes=4),
                "signal_id": 41,
            },  # Loss Breaker for profit clusters
        ]
    )
    sigs_toxic1 = pd.DataFrame(
        [
            {
                "id": 10,
                "algorithm": "A",
                "direction": 1,
                "volatility": 0.1,
                "created_at": t1 - pd.Timedelta(minutes=5),
            },
            {
                "id": 11,
                "algorithm": "B",
                "direction": 1,
                "volatility": 0.1,
                "created_at": t1 - pd.Timedelta(minutes=4),
            },
        ]
    )

    # Toxic Instance 2 (next day, same hour)
    t2 = t1 + pd.Timedelta(days=1)
    trades_toxic2 = pd.DataFrame(
        [
            {"id": 5, "pnl": -10, "created_at": t2, "signal_id": 5},
            {"id": 6, "pnl": -10, "created_at": t2 + pd.Timedelta(minutes=1), "signal_id": 6},
            {"id": 7, "pnl": -10, "created_at": t2 + pd.Timedelta(minutes=2), "signal_id": 7},
            {
                "id": 8,
                "pnl": 10,
                "created_at": t2 + pd.Timedelta(minutes=3),
                "signal_id": 8,
            },  # Win Breaker
            {
                "id": 81,
                "pnl": -10,
                "created_at": t2 + pd.Timedelta(minutes=4),
                "signal_id": 81,
            },  # Loss Breaker
        ]
    )
    sigs_toxic2 = pd.DataFrame(
        [
            {
                "id": 20,
                "algorithm": "A",
                "direction": 1,
                "volatility": 0.1,
                "created_at": t2 - pd.Timedelta(minutes=5),
            },
            {
                "id": 21,
                "algorithm": "B",
                "direction": 1,
                "volatility": 0.1,
                "created_at": t2 - pd.Timedelta(minutes=4),
            },
        ]
    )

    # Golden Instance 1 (at 14:00)
    t3 = base_time + pd.Timedelta(hours=4)
    trades_golden1 = pd.DataFrame(
        [
            {"id": 100, "pnl": 50, "created_at": t3, "signal_id": 100},
            {"id": 101, "pnl": 50, "created_at": t3 + pd.Timedelta(minutes=1), "signal_id": 101},
            {"id": 102, "pnl": 50, "created_at": t3 + pd.Timedelta(minutes=2), "signal_id": 102},
            {
                "id": 103,
                "pnl": -10,
                "created_at": t3 + pd.Timedelta(minutes=3),
                "signal_id": 103,
            },  # Loss Breaker
            {
                "id": 104,
                "pnl": 10,
                "created_at": t3 + pd.Timedelta(minutes=4),
                "signal_id": 104,
            },  # Win Breaker for drawdown clusters
        ]
    )
    sigs_golden1 = pd.DataFrame(
        [
            {
                "id": 110,
                "algorithm": "X",
                "direction": 1,
                "volatility": 0.1,
                "created_at": t3 - pd.Timedelta(minutes=5),
            },
            {
                "id": 111,
                "algorithm": "Y",
                "direction": 1,
                "volatility": 0.1,
                "created_at": t3 - pd.Timedelta(minutes=4),
            },
        ]
    )

    # Golden Instance 2 (next day, same hour)
    t4 = t3 + pd.Timedelta(days=1)
    trades_golden2 = pd.DataFrame(
        [
            {"id": 200, "pnl": 50, "created_at": t4, "signal_id": 200},
            {"id": 201, "pnl": 50, "created_at": t4 + pd.Timedelta(minutes=1), "signal_id": 201},
            {"id": 202, "pnl": 50, "created_at": t4 + pd.Timedelta(minutes=2), "signal_id": 202},
            {
                "id": 203,
                "pnl": -10,
                "created_at": t4 + pd.Timedelta(minutes=3),
                "signal_id": 203,
            },  # Loss Breaker
            {
                "id": 204,
                "pnl": 10,
                "created_at": t4 + pd.Timedelta(minutes=4),
                "signal_id": 204,
            },  # Win Breaker
        ]
    )
    sigs_golden2 = pd.DataFrame(
        [
            {
                "id": 210,
                "algorithm": "X",
                "direction": 1,
                "volatility": 0.1,
                "created_at": t4 - pd.Timedelta(minutes=5),
            },
            {
                "id": 211,
                "algorithm": "Y",
                "direction": 1,
                "volatility": 0.1,
                "created_at": t4 - pd.Timedelta(minutes=4),
            },
        ]
    )

    all_trades = pd.concat(
        [trades_toxic1, trades_toxic2, trades_golden1, trades_golden2]
    ).sort_values("created_at")
    all_sigs = pd.concat([sigs_toxic1, sigs_toxic2, sigs_golden1, sigs_golden2])

    motifs = miner.find_combination_motifs(all_sigs, all_trades)
    assert len(motifs) == 2
    toxic = next(m for m in motifs if "A:1" in m.patterns)
    assert toxic.is_toxic is True
    golden = next(m for m in motifs if "X:1" in m.patterns)
    assert golden.is_golden is True


def test_find_frequent_motifs_with_clusters(miner):
    now = datetime.now(timezone.utc)
    trades = pd.DataFrame(
        [
            {"id": 1, "pnl": -10, "created_at": now, "signal_id": 1},
            {"id": 2, "pnl": -10, "created_at": now + pd.Timedelta(minutes=1), "signal_id": 2},
            {"id": 3, "pnl": -10, "created_at": now + pd.Timedelta(minutes=2), "signal_id": 3},
            {"id": 8, "pnl": 10, "created_at": now + pd.Timedelta(minutes=3), "signal_id": 8},
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


def test_combination_motif_attributes(miner):
    from src.analytics.journal_mining import CombinationMotif

    motif = CombinationMotif(
        patterns=["A:1", "B:-1"],
        frequency=5,
        avg_pnl_after=-50.0,
        is_toxic=True,
        session="London",
        volatility_bucket="High",
    )
    assert motif.session == "London"
    assert motif.volatility_bucket == "High"
    assert motif.is_toxic is True


def test_detect_revenge_trading(miner):
    now = datetime.now(timezone.utc)
    trades = pd.DataFrame(
        [
            {"id": 1, "pnl": -100.0, "lot_size": 0.1, "created_at": now},
            {"id": 2, "pnl": 50.0, "lot_size": 0.2, "created_at": now + pd.Timedelta(minutes=10)},
            {"id": 3, "pnl": -50.0, "lot_size": 0.1, "created_at": now + pd.Timedelta(hours=2)},
            {
                "id": 4,
                "pnl": -20.0,
                "lot_size": 0.1,
                "created_at": now + pd.Timedelta(hours=2, minutes=5),
            },
        ]
    )

    revenge = miner.detect_revenge_trading(trades)
    assert len(revenge) == 2
    # First revenge trade: id 2 after id 1 (10 mins, lot increase)
    assert revenge[0].trade_id == 2
    assert revenge[0].lot_increase is True
    # Second revenge trade: id 4 after id 3 (5 mins, no lot increase)
    assert revenge[1].trade_id == 4
    assert revenge[1].lot_increase is False


def test_profitable_patterns_extended(miner):
    now = datetime.now(timezone.utc)
    trades = pd.DataFrame(
        [
            {
                "id": 1,
                "pnl": 100.0,
                "algorithm": "ensemble",
                "volatility": 0.05,
                "confidence": 0.85,
                "created_at": now,
            },
            {
                "id": 2,
                "pnl": 50.0,
                "algorithm": "ensemble",
                "volatility": 0.06,
                "confidence": 0.82,
                "created_at": now + pd.Timedelta(minutes=5),
            },
        ]
    )

    patterns = miner.find_profitable_patterns(trades)
    # Check algo_volatility
    algo_vol = [p for p in patterns if p.attribute == "algo_volatility"]
    assert len(algo_vol) == 1
    assert algo_vol[0].value == "ensemble @ Low Vol"

    # Check algo_confidence
    algo_conf = [p for p in patterns if p.attribute == "algo_confidence"]
    assert len(algo_conf) == 1
    assert algo_conf[0].value == "ensemble @ High Conf"


def test_analyze_session_overlaps(miner):
    # Sydney (22-07) and Tokyo (00-09) overlap from 00 to 07
    now = datetime(2024, 1, 1, 2, 0, tzinfo=timezone.utc)
    trades = pd.DataFrame(
        [
            {"id": 1, "pnl": 100.0, "created_at": now},
            {"id": 2, "pnl": -50.0, "created_at": now + pd.Timedelta(minutes=5)},
        ]
    )

    overlaps = miner.analyze_session_overlaps(trades)
    assert len(overlaps) == 1
    assert overlaps[0].attribute == "session_overlap"
    assert "Sydney / Tokyo" in overlaps[0].value
    assert overlaps[0].total_trades == 2


def test_report_mapping_includes_total_trades(miner):
    from src.analytics.journal_mining import JournalReport, PatternConcentration

    report = JournalReport(
        session_analysis=[],
        volatility_patterns=[],
        drawdown_clusters=[],
        profitable_concentrations=[
            PatternConcentration(
                attribute="algo", value="ppo", win_rate=0.6, profit_factor=2.1, total_trades=150
            )
        ],
        risk_block_summary=[],
    )

    section = report.to_report_section()
    assert section.concentrations[0].total_trades == 150


def test_report_includes_revenge_trading_risk(miner):
    from src.analytics.journal_mining import JournalReport

    report = JournalReport(
        session_analysis=[],
        volatility_patterns=[],
        drawdown_clusters=[],
        profitable_concentrations=[],
        risk_block_summary=[],
        revenge_trades=[
            {
                "trade_id": 2,
                "prev_trade_id": 1,
                "time_diff_min": 5.0,
                "lot_increase": True,
                "pnl": -50,
            }
        ],
    )

    section = report.to_report_section()
    revenge_risk = next((r for r in section.behavioral_risks if r.type == "Revenge Trading"), None)
    assert revenge_risk is not None
    assert "TILT" in revenge_risk.description


def test_analyze_rejection_quality(miner):
    blocked_df = pd.DataFrame(
        [
            {"rejection_reason": "SPREAD", "would_have_won": False, "opportunity_cost_pnl": 0.0},
            {"rejection_reason": "SPREAD", "would_have_won": True, "opportunity_cost_pnl": 50.0},
            {"rejection_reason": "MAX_DD", "would_have_won": False, "opportunity_cost_pnl": 0.0},
        ]
    )

    qualities = miner.analyze_rejection_quality(blocked_df)
    assert len(qualities) == 2

    spread = next(q for q in qualities if q.reason == "SPREAD")
    assert spread.total_blocked == 2
    assert spread.correct_blocks == 1
    assert spread.incorrect_blocks == 1
    assert spread.accuracy == 0.5
    assert spread.profit_opportunity_cost == 50.0


def test_analyze_blocked_motifs(miner):
    signals = pd.DataFrame(
        [
            {
                "id": 1,
                "algorithm": "ensemble",
                "direction": 1,
                "volatility": 0.05,
                "confidence": 0.85,
                "created_at": datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc),
            },
            {
                "id": 2,
                "algorithm": "ensemble",
                "direction": 1,
                "volatility": 0.05,
                "confidence": 0.85,
                "created_at": datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
            },
        ]
    )
    blocked = pd.DataFrame(
        [
            {"signal_id": 1, "opportunity_cost_pnl": 100.0, "would_have_won": True},
            {"signal_id": 2, "opportunity_cost_pnl": 50.0, "would_have_won": True},
        ]
    )

    motifs = miner.analyze_blocked_motifs(signals, blocked)
    assert len(motifs) == 1
    assert motifs[0].algorithm == "ensemble"
    assert motifs[0].is_golden is True


def test_detect_overconfidence(miner):
    now = datetime.now(timezone.utc)
    # 3 consecutive wins followed by a lot increase
    trades = pd.DataFrame(
        [
            {"id": 1, "pnl": 10.0, "lot_size": 0.1, "created_at": now},
            {"id": 2, "pnl": 20.0, "lot_size": 0.1, "created_at": now + pd.Timedelta(minutes=5)},
            {"id": 3, "pnl": 15.0, "lot_size": 0.1, "created_at": now + pd.Timedelta(minutes=10)},
            {"id": 4, "pnl": -5.0, "lot_size": 0.2, "created_at": now + pd.Timedelta(minutes=15)},
        ]
    )

    overconfidence = miner.detect_overconfidence(trades, consecutive_wins_threshold=3)
    assert len(overconfidence) == 1
    assert overconfidence[0].trade_id == 4
    assert overconfidence[0].consecutive_wins == 3
    assert overconfidence[0].lot_increase_pct == 1.0


def test_run_mining_enhanced(miner):
    from src.core.trade_logger import BlockedSignalAnalysis, ModelSignal, Trade

    with miner.Session() as session:
        # Closed trade for overconfidence detection (need 4 trades)
        for i in range(4):
            sig = ModelSignal(
                symbol="XAUUSD",
                direction=1,
                entry_price=2000.0,
                algorithm="ppo",
                confidence=0.8,
                volatility=0.1,
            )
            session.add(sig)
            session.commit()

            t = Trade(
                ticket=1000 + i,
                symbol="XAUUSD",
                direction=1,
                entry_price=2000.0,
                lot_size=0.1 if i < 3 else 0.2,
                pnl=10.0 if i < 3 else -5.0,
                status="CLOSED",
                signal_id=sig.id,
            )
            t.created_at = datetime.now(timezone.utc) + pd.Timedelta(minutes=i)
            session.add(t)

        # Blocked signal for rejection quality
        sig2 = ModelSignal(
            symbol="XAUUSD", direction=-1, entry_price=2000.0, algorithm="ppo", confidence=0.8
        )
        session.add(sig2)
        session.commit()

        blocked = BlockedSignalAnalysis(
            signal_id=sig2.id,
            opportunity_cost_pnl=100.0,
            max_favorable_excursion=110.0,
            max_adverse_excursion=10.0,
            would_have_won=True,
            rejection_reason="RISK_LIMIT",
        )
        session.add(blocked)
        session.commit()

    report = miner.run_mining()
    assert len(report.rejection_quality) == 1
    assert report.rejection_quality[0].reason == "RISK_LIMIT"
    assert report.rejection_quality[0].profit_opportunity_cost == 100.0
    assert len(report.overconfidence_events) == 1
    assert report.overconfidence_events[0].consecutive_wins == 3


def test_session_stats_z_score(miner, sample_trades):
    stats = miner.get_session_stats(sample_trades)
    # Check that z_score is calculated
    for s in stats:
        assert hasattr(s, "z_score")

    # Statistical overtrading (if we add many trades to one session)
    many_trades = pd.concat([sample_trades] * 10)
    stats_many = miner.get_session_stats(many_trades)
    # With balanced distribution, Z-score might still be low.
    # We don't assert specific value but existence.
    assert all(isinstance(s.z_score, float) for s in stats_many)


def test_analyze_performance_decay(miner):
    # Setup data with a clear decay
    # Baseline (20 trades): PF = 2.0
    baseline = pd.DataFrame(
        [
            {"pnl": 100.0, "created_at": datetime(2024, 1, 1, i, 0, tzinfo=timezone.utc)}
            for i in range(10)
        ]
        + [
            {"pnl": -50.0, "created_at": datetime(2024, 1, 1, i + 10, 0, tzinfo=timezone.utc)}
            for i in range(10)
        ]
    )

    # Recent (20 trades): PF = 0.5
    recent = pd.DataFrame(
        [
            {"pnl": 50.0, "created_at": datetime(2024, 1, 2, i, 0, tzinfo=timezone.utc)}
            for i in range(10)
        ]
        + [
            {"pnl": -100.0, "created_at": datetime(2024, 1, 2, i + 10, 0, tzinfo=timezone.utc)}
            for i in range(10)
        ]
    )

    all_trades = pd.concat([baseline, recent])
    decay = miner.analyze_performance_decay(all_trades, window_size=20)

    assert decay is not None
    assert decay.is_decaying is True
    assert decay.baseline_pf == 2.0
    assert decay.recent_pf == 0.5
    assert decay.profit_factor_trend == -0.75  # (0.5 - 2.0) / 2.0


def test_to_report_section_enhanced_risks(miner):
    from src.analytics.journal_mining import (
        JournalReport,
        OverconfidenceEvent,
        RejectionQuality,
        SignalMotif,
    )

    report = JournalReport(
        session_analysis=[],
        volatility_patterns=[],
        drawdown_clusters=[],
        profitable_concentrations=[],
        risk_block_summary=[],
        overconfidence_events=[
            OverconfidenceEvent(trade_id=4, consecutive_wins=3, lot_increase_pct=1.0, pnl=-5.0)
        ],
        rejection_quality=[
            RejectionQuality(
                reason="DUMMY",
                total_blocked=5,
                correct_blocks=1,
                incorrect_blocks=4,
                accuracy=0.2,
                profit_opportunity_cost=500.0,
            )
        ],
        blocked_motifs=[
            SignalMotif(
                algorithm="transformer",
                direction=1,
                volatility_bucket="Normal",
                confidence_bucket="High",
                session="London",
                frequency=3,
                win_rate=0.8,
                is_golden=True,
                expectancy=100,
            )
        ],
    )

    section = report.to_report_section()
    risk_types = [r.type for r in section.behavioral_risks]
    assert "Overconfidence" in risk_types
    assert "Poor Rejection Quality" in risk_types
    assert "Missed Opportunity" in risk_types
    assert "missed 500.00" in section.behavioral_risks[1].description
