
import os
import sqlite3
import logging
from src.core.database import get_engine

logging.basicConfig(level=logging.DEBUG)

def verify_pragmas():
    db_path = "test_verify_pragmas.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    db_url = f"sqlite:///{db_path}"
    engine = get_engine(db_url)

    try:
        with engine.connect() as conn:
            # Verify WAL mode
            journal_mode = conn.exec_driver_sql("PRAGMA journal_mode").scalar()
            print(f"journal_mode: {journal_mode}")
            assert journal_mode.lower() == "wal"

            # Verify Foreign Keys
            foreign_keys = conn.exec_driver_sql("PRAGMA foreign_keys").scalar()
            print(f"foreign_keys: {foreign_keys}")
            assert foreign_keys == 1

            # Verify Busy Timeout
            busy_timeout = conn.exec_driver_sql("PRAGMA busy_timeout").scalar()
            print(f"busy_timeout: {busy_timeout}")
            assert busy_timeout == 5000

            # Verify Synchronous
            synchronous = conn.exec_driver_sql("PRAGMA synchronous").scalar()
            print(f"synchronous: {synchronous}")
            # 1 = NORMAL
            assert synchronous == 1

        print("--- All pragmas verified successfully ---")
        return True
    except Exception as e:
        print(f"Pragma verification FAILED: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
        for suffix in ["-wal", "-shm"]:
            if os.path.exists(db_path + suffix):
                os.remove(db_path + suffix)

if __name__ == "__main__":
    import sys
    if verify_pragmas():
        sys.exit(0)
    else:
        sys.exit(1)
