"""
MT5 AI/ML Trading Bot - Migration Safety Script
Automates the verification of Alembic migrations by performing
an upgrade-downgrade-upgrade cycle on a temporary database.
"""
import os
import sys

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

        # 2. Downgrade to base (full reversal)
        print("--- Step 2: Downgrading to base ---")
        command.downgrade(alembic_cfg, "base")

        # 3. Upgrade to head again
        print("--- Step 3: Upgrading to head again ---")
        command.upgrade(alembic_cfg, "head")

        # 4. Check for schema drift (models vs migrations)
        print("--- Step 4: Checking for schema drift (alembic check) ---")
        # alembic check was added in Alembic 1.9.0
        try:
            command.check(alembic_cfg)
            print("--- Schema Drift Check PASSED ---")
        except Exception as drift_error:
            print("="*60)
            print("  DEPLOYMENT BLOCKED: SCHEMA DRIFT DETECTED")
            print("  (Models changed without corresponding migrations)")
            print("="*60)
            raise drift_error

        print("--- Migration Reversibility & Drift Check PASSED ---")
        return True

    except Exception as e:
        print("="*60)
        print("  DEPLOYMENT BLOCKED: MIGRATION VERIFICATION FAILED")
        print("="*60)
        print(f"Error during migration verification: {e}")
        import traceback
        traceback.print_exc()
        print("="*60)
        return False

    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)

if __name__ == "__main__":
    if not verify_migrations():
        sys.exit(1)
    sys.exit(0)
