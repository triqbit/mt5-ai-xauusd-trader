"""
Unit tests for centralized database utility.
"""

from sqlalchemy.pool import NullPool, StaticPool

from src.core.database import get_engine, verify_engine


def test_get_engine_memory_sqlite():
    """Test that in-memory SQLite uses StaticPool."""
    url = "sqlite:///:memory:"
    engine = get_engine(url)
    assert engine.url.database == ":memory:"
    assert isinstance(engine.pool, StaticPool)

def test_get_engine_file_sqlite():
    """Test that file-based SQLite uses NullPool."""
    url = "sqlite:///test_engine.db"
    engine = get_engine(url)
    assert isinstance(engine.pool, NullPool)

def test_engine_caching():
    """Test that engines are cached by URL."""
    url = "sqlite:///:memory:"
    engine1 = get_engine(url)
    engine2 = get_engine(url)
    assert engine1 is engine2

def test_verify_engine():
    """Test engine verification utility."""
    engine = get_engine("sqlite:///:memory:")
    assert verify_engine(engine) is True
