from datetime import datetime, timezone

import pandas as pd

from src.analytics.journal_mining import (
    BlockReasonSummary,
    JournalMiner,
    JournalReport,
    PerformanceDecay,
)


def test_institutional_thresholds():
    assert JournalMiner.Z_SCORE_THRESHOLD == 1.5
    assert JournalMiner.PF_DECAY_THRESHOLD == -0.3
    assert JournalMiner.WEAK_STATE_CORRELATION == 0.7


def test_overtrading_alert_z_score():
    miner = JournalMiner(db_url="sqlite:///:memory:")
    # Create unbalanced session distribution to trigger Z-score
    # London: 10 trades, Sydney: 1 trade, Tokyo: 1 trade, New York: 1 trade
    trades = []
    for _ in range(10):
        trades.append({"created_at": datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc), "pnl": 10.0})
    for h in [23, 1, 14]:
        trades.append({"created_at": datetime(2024, 1, 1, h, 0, tzinfo=timezone.utc), "pnl": 10.0})

    df = pd.DataFrame(trades)
    stats = miner.get_session_stats(df)

    london = next(s for s in stats if s.session_name == "London")
    assert london.is_overtrading is True
    assert london.z_score > 1.5


def test_alpha_decay_mapping():
    report = JournalReport(
        session_analysis=[],
        volatility_patterns=[],
        drawdown_clusters=[],
        profitable_concentrations=[],
        risk_block_summary=[],
        performance_decay=PerformanceDecay(
            window_size=20,
            profit_factor_trend=-0.35,
            is_decaying=True,
            recent_pf=0.8,
            baseline_pf=1.23,
        ),
    )

    section = report.to_report_section()
    risk_types = [r.type for r in section.behavioral_risks]
    assert "Alpha Decay" in risk_types
    assert "dropped by 35.0%" in section.behavioral_risks[0].description


def test_strategy_fragility_mapping():
    report = JournalReport(
        session_analysis=[],
        volatility_patterns=[],
        drawdown_clusters=[],
        profitable_concentrations=[],
        risk_block_summary=[
            BlockReasonSummary(
                reason="MAX_DD", count=5, impacted_algorithms=["ppo"], weak_state_correlation=0.75
            )
        ],
    )

    section = report.to_report_section()
    risk_types = [r.type for r in section.behavioral_risks]
    assert "Strategy Fragility" in risk_types
    assert "Cluster Warning" in risk_types  # 0.75 > 0.6 as well
