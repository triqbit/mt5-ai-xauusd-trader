import os
import stat
import sys

import pytest

from src.core.database import get_engine


@pytest.mark.skipif(sys.platform == "win32", reason="Permission check only on Linux/Mac")
def test_sqlite_file_permissions_hardening(tmp_path):
    """
    Verify that get_engine enforces 0o600 permissions on new SQLite database files.
    """
    db_file = tmp_path / "secure_test.db"
    db_url = f"sqlite:///{db_file}"

    # Ensure get_engine cache doesn't interfere
    get_engine.cache_clear()

    # 1. Test creation of new file
    get_engine(db_url)

    assert db_file.exists()
    mode = stat.S_IMODE(db_file.stat().st_mode)
    assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"

    # 2. Test hardening of existing file
    os.chmod(db_file, 0o644)
    assert stat.S_IMODE(db_file.stat().st_mode) == 0o644

    get_engine.cache_clear()
    get_engine(db_url)

    mode = stat.S_IMODE(db_file.stat().st_mode)
    assert mode == 0o600, f"Expected hardening to 0o600, got {oct(mode)}"


def test_sqlite_in_memory_no_file_creation():
    """
    Verify that in-memory SQLite doesn't attempt to create a file.
    """
    get_engine.cache_clear()
    # This should not raise any exceptions or create files
    get_engine("sqlite:///:memory:")
    get_engine("sqlite://")
