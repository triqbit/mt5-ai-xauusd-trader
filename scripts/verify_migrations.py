"""
MT5 AI/ML Trading Bot - Migration Safety Script
Automates the verification of Alembic migrations by performing
an upgrade-downgrade-upgrade cycle on a temporary database.
Includes a schema drift check to ensure models and migrations are in sync.
"""
import os
import sys
from unittest.mock import MagicMock

# Mock talib to allow running in environments without the C library (like CI)
sys.modules["talib"] = MagicMock()

from alembic import command
from alembic.config import Config


def verify_migrations():
    temp_db = "test_migrations.db"
    if os.path.exists(temp_db):
        os.remove(temp_db)

    temp_url = f"sqlite:///{temp_db}"

    # Load the Alembic configuration
    alembic_cfg = Config("alembic.ini")
    # Override the database URL to use our temporary test database
    alembic_cfg.set_main_option("sqlalchemy.url", temp_url)

    try:
        # 1. Upgrade to head
        print("--- Step 1: Upgrading to head ---")
        command.upgrade(alembic_cfg, "head")

        # 2. Schema Drift Check (Ensures no missing migrations)
        print("--- Step 2: Checking for schema drift ---")
        try:
            command.check(alembic_cfg)
            print("--- Schema Drift Check PASSED ---")
        except Exception as drift_err:
            print("=" * 60)
            print("  DEPLOYMENT BLOCKED: SCHEMA DRIFT DETECTED")
            print("=" * 60)
            print("Your SQLAlchemy models do not match the current migration state.")
            print(f"Details: {drift_err}")
            print("\nREMEDIATION: Run 'alembic revision --autogenerate' to create a new migration.")
            print("=" * 60)
            return False

        # 3. Downgrade to base (full reversal)
        print("--- Step 3: Downgrading to base ---")
        command.downgrade(alembic_cfg, "base")

        # 4. Upgrade to head again
        print("--- Step 4: Upgrading to head again ---")
        command.upgrade(alembic_cfg, "head")

        print("--- Migration Reversibility Check PASSED ---")
        return True

    except Exception as e:
        print("=" * 60)
        print("  DEPLOYMENT BLOCKED: MIGRATION VERIFICATION FAILED")
        print("=" * 60)
        print(f"Error during migration verification: {e}")
        print("\nREMEDIATION: Check for SQL syntax errors, broken references, or")
        print("non-reversible operations (missing downgrade logic) in migrations/versions/.")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        return False

    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)

if __name__ == "__main__":
    if not verify_migrations():
        sys.exit(1)
    sys.exit(0)
