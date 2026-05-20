"""
MT5 AI/ML Trading Bot - Migration Safety Test
tests/test_migration_safety.py
Verifies that the migration safety script correctly detects valid migrations.
"""
import os

from scripts.verify_migrations import verify_migrations


def test_verify_migrations_logic():
    """
    Ensures verify_migrations returns True for the current set of migrations.
    This also tests that the script can run without error in the test environment.
    """
    # The script uses a temporary database and cleans it up.
    # It should pass if the current migrations are reversible.
    assert verify_migrations() is True

def test_verify_migrations_cleanup():
    """
    Ensures that the temporary database file is removed after the check.
    """
    temp_db = "test_migrations.db"
    # Ensure it's gone before
    if os.path.exists(temp_db):
        os.remove(temp_db)

    verify_migrations()

    # Ensure it's gone after
    assert not os.path.exists(temp_db)
