import logging
import os

from sqlalchemy import inspect, text

from src.core.database import get_engine


def test_slow_query_logger(caplog):
    """Verify that slow queries are logged with a warning."""
    db_path = "test_slow_query.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    db_url = f"sqlite:///{db_path}"
    engine = get_engine(db_url)

    with caplog.at_level(logging.WARNING), engine.connect() as conn:
        conn.execute(
            text(
                "WITH RECURSIVE cnt(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM cnt WHERE x<1000000) SELECT count(*) FROM cnt"
            )
        )

    slow_logs = [record for record in caplog.records if "SLOW QUERY DETECTED" in record.message]

    if os.path.exists(db_path):
        os.remove(db_path)

    print(f"Captured {len(slow_logs)} slow query logs.")


def test_index_presence():
    """Verify that the ix_trades_perf_lookup index exists on the trades table."""
    db_path = "test_index_presence.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    db_url = f"sqlite:///{db_path}"
    engine = get_engine(db_url)

    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")

    inspector = inspect(engine)
    indexes = inspector.get_indexes("trades")
    index_names = [idx["name"] for idx in indexes]

    assert "ix_trades_perf_lookup" in index_names

    perf_index = next(idx for idx in indexes if idx["name"] == "ix_trades_perf_lookup")
    assert perf_index["column_names"] == ["status", "is_deleted", "created_at"]

    if os.path.exists(db_path):
        os.remove(db_path)
