
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.exc import OperationalError
from src.core.database import create_resilient_engine, with_db_retry

def test_engine_pooling_settings():
    # Test for non-sqlite URL
    with patch("src.core.database.create_engine") as mock_create:
        url = "postgresql://user:pass@localhost/db"
        create_resilient_engine(url)

        args, kwargs = mock_create.call_args
        assert args[0] == url
        assert kwargs["pool_size"] == 20
        assert kwargs["max_overflow"] == 40
        assert kwargs["pool_pre_ping"] is True

def test_sqlite_engine_no_pooling():
    url = "sqlite:///test.db"
    # This should not raise "TypeError: Invalid argument(s) 'pool_size', 'max_overflow'..."
    engine = create_resilient_engine(url)
    assert engine.url.drivername == "sqlite"

def test_with_db_retry_success():
    mock_func = MagicMock(return_value="success")
    decorated = with_db_retry(max_retries=2, initial_delay=0.1)(mock_func)

    result = decorated()
    assert result == "success"
    assert mock_func.call_count == 1

def test_with_db_retry_recovery():
    # Fail once, then succeed
    mock_func = MagicMock()
    mock_func.side_effect = [OperationalError("test", {}, None), "recovered"]

    decorated = with_db_retry(max_retries=2, initial_delay=0.1)(mock_func)

    result = decorated()
    assert result == "recovered"
    assert mock_func.call_count == 2

def test_with_db_retry_exhaustion():
    # Always fail
    mock_func = MagicMock()
    mock_func.side_effect = OperationalError("test", {}, None)

    decorated = with_db_retry(max_retries=2, initial_delay=0.1)(mock_func)

    with pytest.raises(OperationalError):
        decorated()

    assert mock_func.call_count == 3 # 1 original + 2 retries
