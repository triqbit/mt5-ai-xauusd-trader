
import os

import pytest
from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import declarative_base

from src.core.database import get_engine, get_session_factory

Base = declarative_base()

class Parent(Base):
    __tablename__ = 'test_parents'
    id = Column(Integer, primary_key=True)

class Child(Base):
    __tablename__ = 'test_children'
    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey('test_parents.id'))

@pytest.fixture
def sqlite_engine():
    db_path = "test_hardening.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    db_url = f"sqlite:///{db_path}"
    engine = get_engine(db_url)
    yield engine

    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)
    for suffix in ["-wal", "-shm"]:
        if os.path.exists(db_path + suffix):
            os.remove(db_path + suffix)

def test_sqlite_pragmas(sqlite_engine):
    """Verify that WAL mode and Foreign Keys are enabled."""
    with sqlite_engine.connect() as conn:
        journal_mode = conn.exec_driver_sql("PRAGMA journal_mode").scalar()
        assert journal_mode.lower() == "wal"

        foreign_keys = conn.exec_driver_sql("PRAGMA foreign_keys").scalar()
        assert foreign_keys == 1

def test_foreign_key_enforcement(sqlite_engine):
    """Verify that Foreign Key constraints are actually enforced by SQLite."""
    Base.metadata.create_all(sqlite_engine)
    Session = get_session_factory(sqlite_engine)

    from sqlalchemy.exc import IntegrityError
    with Session() as session:
        # Attempt to insert a child with a non-existent parent
        child = Child(id=1, parent_id=999)
        session.add(child)
        with pytest.raises(IntegrityError) as excinfo:
            session.commit()
        assert "FOREIGN KEY constraint failed" in str(excinfo.value)
        session.rollback()
