import os
import sys
from unittest.mock import MagicMock

# Mock talib before any imports
sys.modules["talib"] = MagicMock()
sys.modules["MetaTrader5"] = MagicMock()

from sqlalchemy import create_engine  # noqa: E402  # noqa: E402


def verify_db(db_url="sqlite:///trades.db"):
    if not os.path.exists(db_url.replace("sqlite:///", "")):
        print(f"Database {db_url} not found.")
        return False

    engine = create_engine(db_url)
    # ... rest of file (I'll fix head only)
