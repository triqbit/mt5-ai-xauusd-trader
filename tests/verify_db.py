import os
import sys
from unittest.mock import MagicMock

# Mock talib before any imports
sys.modules["talib"] = MagicMock()
sys.modules["MetaTrader5"] = MagicMock()

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from src.core.trade_logger import Base, ModelSignal, RiskEvent, Trade  # noqa: E402


def verify_db(db_url="sqlite:///trades.db"):
    if not os.path.exists(db_url.replace("sqlite:///", "")):
        print(f"Database {db_url} not found.")
        return False

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        signals = session.query(ModelSignal).all()
        trades = session.query(Trade).all()
        events = session.query(RiskEvent).all()

        print(f"Signals: {len(signals)}")
        print(f"Trades: {len(trades)}")
        print(f"Risk Events: {len(events)}")

        # Verify linking
        linked_trades = 0
        for t in trades:
            if t.signal_id is not None:
                linked_trades += 1

        print(f"Linked Trades: {linked_trades}")

        if len(trades) > 0 and linked_trades == 0:
            print("Consistency Error: Trades exist but none are linked to signals.")
            return False

    return True

if __name__ == "__main__":
    # Test with a temporary DB to ensure script works
    test_db = "sqlite:///test_verify.db"
    engine = create_engine(test_db)
    Base.metadata.create_all(engine)

    success = verify_db(test_db)
    if os.path.exists("test_verify.db"):
        os.remove("test_verify.db")

    if success:
        print("Verification script logic works.")
        sys.exit(0)
    else:
        print("Verification script logic failed.")
        sys.exit(1)
