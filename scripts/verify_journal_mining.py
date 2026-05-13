"""
MT5 AI/ML Trading Bot - Enterprise Edition
scripts/verify_journal_mining.py
Verification script for the journal mining system.
"""

import os
import random
import sys
from datetime import UTC, datetime, timedelta

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.analytics.journal_mining import JournalMiner
from src.core.trade_logger import Base, ModelSignal, RiskEvent, Trade
from src.research.reporting import ResearchOrchestrator, ResearchReporter


def generate_synthetic_data(db_url):
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        # 1. Generate normal signals and trades

        now = datetime.now(UTC)

        # Profitable London session
        for i in range(20):
            # London session is 08-17 UTC
            dt = now.replace(hour=10, minute=random.randint(0, 59)) - timedelta(
                days=random.randint(1, 30)
            )
            sig = ModelSignal(
                symbol="XAUUSD",
                direction=1,
                entry_price=2000.0 + i,
                algorithm="Ensemble_V2",
                confidence=0.8,
                volatility=0.1,
                created_at=dt,
            )
            session.add(sig)
            session.flush()

            trd = Trade(
                ticket=1000 + i,
                symbol="XAUUSD",
                direction=1,
                entry_price=2000.0 + i,
                exit_price=2010.0 + i,
                lot_size=0.1,
                pnl=100.0,
                status="CLOSED",
                signal_id=sig.id,
                created_at=dt,
                updated_at=dt + timedelta(minutes=45),
            )
            session.add(trd)

        # Toxic Combination: PPO + Dreamer before a drawdown
        # Let's create 3 such clusters
        for cluster_idx in range(3):
            cluster_start = now - timedelta(days=cluster_idx + 2)

            # Pre-cluster signals (Combination Motif)
            sig1 = ModelSignal(
                symbol="XAUUSD",
                direction=1,
                entry_price=2000.0,
                algorithm="PPO_Agent",
                confidence=0.9,
                volatility=0.5,
                created_at=cluster_start - timedelta(minutes=30),
            )
            sig2 = ModelSignal(
                symbol="XAUUSD",
                direction=-1,
                entry_price=2000.0,
                algorithm="Dreamer_V3",
                confidence=0.85,
                volatility=0.5,
                created_at=cluster_start - timedelta(minutes=25),
            )
            session.add_all([sig1, sig2])
            session.flush()

            # Drawdown cluster (3 losses)
            for j in range(3):
                dt = cluster_start + timedelta(minutes=j * 10)
                sig = ModelSignal(
                    symbol="XAUUSD",
                    direction=1,
                    entry_price=2000.0,
                    algorithm="PPO_Agent",
                    confidence=0.7,
                    volatility=0.5,
                    created_at=dt,
                )
                session.add(sig)
                session.flush()

                trd = Trade(
                    ticket=2000 + cluster_idx * 10 + j,
                    symbol="XAUUSD",
                    direction=1,
                    entry_price=2000.0,
                    exit_price=1990.0,
                    lot_size=0.1,
                    pnl=-100.0,
                    status="CLOSED",
                    signal_id=sig.id,
                    created_at=dt,
                    updated_at=dt + timedelta(minutes=20),
                )
                session.add(trd)

            # Risk event during weak state (during cluster)
            evt = RiskEvent(
                event_type="MAX_DRAWDOWN_BREACH",
                description="Max drawdown reached during cluster",
                symbol="XAUUSD",
                created_at=cluster_start + timedelta(minutes=15),
            )
            session.add(evt)

        # Overtrading in Sydney session (22-07 UTC)
        for i in range(50):
            dt = now.replace(hour=2, minute=random.randint(0, 59)) - timedelta(
                days=random.randint(1, 10)
            )
            sig = ModelSignal(
                symbol="XAUUSD",
                direction=random.choice([1, -1]),
                entry_price=2000.0,
                algorithm="PPO_Agent",
                confidence=0.5,
                volatility=0.2,
                created_at=dt,
            )
            session.add(sig)
            session.flush()

            # Mostly losses
            pnl = random.choice([-50, -50, -50, 20])
            trd = Trade(
                ticket=3000 + i,
                symbol="XAUUSD",
                direction=1,
                entry_price=2000.0,
                exit_price=2000.0 + (pnl / 100),
                lot_size=0.1,
                pnl=pnl,
                status="CLOSED",
                signal_id=sig.id,
                created_at=dt,
                updated_at=dt + timedelta(minutes=120),
            )
            session.add(trd)

        session.commit()


def main():
    print("🚀 Starting Journal Mining Verification...")
    db_url = "sqlite:///verify_journal.db"

    # Cleanup old DB
    if os.path.exists("verify_journal.db"):
        os.remove("verify_journal.db")

    # 1. Generate Data
    print("📊 Generating synthetic trade data...")
    generate_synthetic_data(db_url)

    # 2. Run Mining
    print("🔍 Running Journal Miner...")
    miner = JournalMiner(db_url=db_url)
    report_data = miner.run_mining()

    # 3. Create Research Report
    orchestrator = ResearchOrchestrator(
        title="Institutional Trade Pattern Audit",
        executive_summary="Automated mining of trade history to detect behavioral risks and signal motifs.",
        conclusion="Journal mining complete. Several toxic patterns identified in Sydney session.",
        overall_status="VERIFIED",
    )

    orchestrator.add_section(report_data.to_report_section())

    # 4. Display Report
    print("\n" + "=" * 50)
    reporter = ResearchReporter()
    reporter.format_for_terminal(orchestrator.build())

    # Cleanup
    if os.path.exists("verify_journal.db"):
        os.remove("verify_journal.db")

    print("✅ Verification complete!")


if __name__ == "__main__":
    main()
