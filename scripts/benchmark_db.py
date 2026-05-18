import time

import numpy as np
from sqlalchemy import Boolean, Column, Float, Integer, String, create_engine, select
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True)
    ticket = Column(Integer)
    symbol = Column(String)
    direction = Column(Integer)
    entry_price = Column(Float)
    exit_price = Column(Float)
    lot_size = Column(Float)
    pnl = Column(Float)
    status = Column(String)
    is_deleted = Column(Boolean, default=False)


def run_benchmark(n_trades=5000):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    # Insert trades
    with Session() as session:
        for i in range(n_trades):
            session.add(
                Trade(
                    ticket=i,
                    symbol="XAUUSD",
                    direction=1,
                    entry_price=2000.0,
                    pnl=np.random.normal(10, 50),
                    status="CLOSED",
                    is_deleted=False,
                )
            )
        session.commit()

    print(f"Benchmarking with {n_trades} trades...")

    # Benchmark 1: ORM Objects (Original slow approach)
    start = time.perf_counter()
    with Session() as session:
        trades = (
            session.query(Trade).filter(Trade.status == "CLOSED", Trade.is_deleted is False).all()
        )
        pnls = np.array([t.pnl for t in trades])
        # Simulate some processing
        np.mean(pnls)
        np.std(pnls)
    duration1 = time.perf_counter() - start
    print(f"ORM All Objects: {duration1:.4f}s")

    # Benchmark 2: Scalar Select (Optimized approach)
    start = time.perf_counter()
    with Session() as session:
        pnls = np.array(
            session.execute(
                select(Trade.pnl).where(Trade.status == "CLOSED", Trade.is_deleted is False)
            )
            .scalars()
            .all()
        )
        # Simulate same processing
        np.mean(pnls)
        np.std(pnls)
    duration2 = time.perf_counter() - start
    print(f"Scalar Select:   {duration2:.4f}s")

    print(f"Speedup: {duration1 / duration2:.2f}x")


if __name__ == "__main__":
    run_benchmark(10000)
