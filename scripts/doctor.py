"""
MT5 AI/ML Trading Bot - Enterprise Diagnostics Tool
scripts/doctor.py
Performs environment, dependency, and connectivity checks to ensure system readiness.
"""

import os
import platform
import sys
from pathlib import Path
import logging

# Configure minimal logging for the doctor
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("doctor")

def check_python_version():
    logger.info("Checking Python version... ")
    version = sys.version_info
    if version.major == 3 and version.minor >= 10:
        logger.info(f"  OK ({platform.python_version()})")
        return True
    else:
        logger.error(f"  FAILED (Requires 3.10+, found {platform.python_version()})")
        return False

def check_dependencies():
    logger.info("Checking core dependencies... ")
    deps = ["numpy", "pandas", "pydantic", "sqlalchemy", "torch", "talib"]
    missing = []
    for dep in deps:
        try:
            __import__(dep)
        except ImportError:
            missing.append(dep)

    if not missing:
        logger.info("  OK")
        return True
    else:
        logger.error(f"  FAILED (Missing: {', '.join(missing)})")
        return False

def check_env_file():
    logger.info("Checking .env file... ")
    if Path(".env").exists():
        logger.info("  OK")
        return True
    else:
        logger.warning("  MISSING (Production requires .env; create one from .env.example)")
        return False

def check_talib():
    logger.info("Checking TA-Lib installation... ")
    try:
        import numpy as np
        import talib
        # Try to call a simple function to ensure the C library is also linked
        talib.SMA(np.array([1.0, 2.0, 3.0]), timeperiod=2)
        logger.info("  OK")
        return True
    except Exception as e:
        logger.warning(f"  FAILED (TA-Lib issue: {e})")
        return True # Non-critical for doctor script itself to run

def check_database_connectivity():
    logger.info("Checking Database connectivity... ")
    try:
        from sqlalchemy import create_engine, text
        # We try to get DATABASE_URL from env manually to avoid Pydantic validation of whole config
        from dotenv import load_dotenv
        load_dotenv()
        db_url = os.getenv("DATABASE_URL", "sqlite:///trades.db")

        engine = create_engine(str(db_url))
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("  OK")
        return True
    except Exception as e:
        logger.error(f"  FAILED (Database issue: {e})")
        return False

def check_redis_connectivity():
    logger.info("Checking Redis connectivity... ")
    try:
        import redis
        from dotenv import load_dotenv
        load_dotenv()
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url)
        r.ping()
        logger.info("  OK")
        return True
    except ImportError:
        logger.warning("  SKIPPED (redis-py not installed)")
        return True
    except Exception as e:
        logger.error(f"  FAILED (Redis issue: {e})")
        return False

def check_mt5_metaapi_config():
    logger.info("Checking MT5/MetaAPI Configuration... ")
    try:
        from dotenv import load_dotenv
        load_dotenv()

        mt5_login = os.getenv("MT5_LOGIN", "0")
        mt5_password = os.getenv("MT5_PASSWORD", "")
        metaapi_token = os.getenv("METAAPI_TOKEN", "")

        has_mt5 = mt5_login != "0" and mt5_password != ""
        has_metaapi = metaapi_token != ""

        if has_mt5:
            logger.info(f"  OK (MT5 Login {mt5_login} configured)")
        elif has_metaapi:
            logger.info("  OK (MetaAPI Token configured)")
        else:
            logger.warning("  WARNING (Neither MT5 nor MetaAPI credentials fully configured)")
            return False
        return True
    except Exception as e:
        logger.error(f"  FAILED (Config issue: {e})")
        return False

def main():
    logger.info("=== MT5 AI/ML Trading Bot Doctor ===")

    # Ensure src is in path if running from scripts/
    sys.path.append(str(Path(__file__).resolve().parents[1]))

    results = [
        check_python_version(),
        check_dependencies(),
        check_env_file(),
        check_talib(),
        check_database_connectivity(),
        check_redis_connectivity(),
        check_mt5_metaapi_config()
    ]

    logger.info("=" * 36)
    if all(results):
        logger.info("System diagnostics complete.")
        sys.exit(0)
    else:
        logger.error("System has CRITICAL ISSUES.")
        sys.exit(1)

if __name__ == "__main__":
    main()
