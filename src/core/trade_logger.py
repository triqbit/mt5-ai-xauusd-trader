"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/trade_logger.py
Institutional-grade trade logging system with SQLAlchemy 2.0.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 style Declarative Base."""

    pass


class AuditMixin:
    """Enterprise audit trail mixin."""

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(50), default="system")
    updated_by = Column(String(50), default="system")
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)


class ModelSignal(Base, AuditMixin):
    """Logs raw signals from the AI ensemble."""

    __tablename__ = "model_signals"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    direction = Column(Integer, nullable=False)  # 1: BUY, -1: SELL, 0: HOLD
    entry_price = Column(Float, nullable=False)
    algorithm = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    volatility = Column(Float)

    # Relationships
    trades = relationship("Trade", back_populates="signal")

    __table_args__ = (
        CheckConstraint("direction IN (-1, 0, 1)", name="valid_direction"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="valid_confidence"),
    )


class Trade(Base, AuditMixin):
    """Logs executed trades and their PnL."""

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True)
    ticket = Column(Integer, unique=True, nullable=False)
    symbol = Column(String(20), nullable=False)
    direction = Column(Integer, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    lot_size = Column(Float, nullable=False)
    pnl = Column(Float, default=0.0)
    status = Column(String(20), default="OPEN")  # OPEN, CLOSED, CANCELLED
    signal_id = Column(Integer, ForeignKey("model_signals.id"))

    # Relationships
    signal = relationship("ModelSignal", back_populates="trades")

    __table_args__ = (
        CheckConstraint("direction IN (-1, 1)", name="valid_trade_direction"),
        CheckConstraint("lot_size > 0", name="positive_lot_size"),
    )


class RiskEvent(Base, AuditMixin):
    """Logs risk management events (e.g., circuit breaker triggers)."""

    __tablename__ = "risk_events"

    id = Column(Integer, primary_key=True)
    event_type = Column(String(50), nullable=False)  # CIRCUIT_BREAKER, SIGNAL_REJECTED
    description = Column(String(255), nullable=False)
    symbol = Column(String(20))
    signal_id = Column(Integer, ForeignKey("model_signals.id"))


class TradeLogger:
    """Enterprise trade logging interface."""

    def __init__(self, db_url: str = "sqlite:///trades.db"):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def log_signal(self, signal_data: Dict[str, Any]) -> int:
        """Log a new model signal to the database."""
        with self.Session() as session:
            signal = ModelSignal(**signal_data)
            session.add(signal)
            session.commit()
            return int(signal.id)

    def log_trade(self, **trade_data) -> int:
        """Log an executed trade."""
        with self.Session() as session:
            trade = Trade(**trade_data)
            session.add(trade)
            session.commit()
            return int(trade.id)

    def update_trade(
        self, ticket: int, exit_price: float, pnl: Optional[float] = None
    ) -> Optional[Trade]:
        """Update a trade upon closure."""
        with self.Session() as session:
            trade = session.query(Trade).filter_by(ticket=ticket).first()
            if trade:
                trade.exit_price = exit_price
                trade.status = "CLOSED"
                if pnl is not None:
                    trade.pnl = pnl
                else:
                    # Automatic calculation based on Gold standard (1 lot = 100oz)
                    multiplier = 100.0 if "XAU" in trade.symbol else 1.0
                    trade.pnl = (
                        (exit_price - trade.entry_price)
                        * trade.direction
                        * trade.lot_size
                        * multiplier
                    )
                session.commit()
                session.refresh(trade)
                return trade
            return None

    def get_trade_by_ticket(self, ticket: int) -> Optional[Trade]:
        """Retrieve trade information by ticket."""
        with self.Session() as session:
            return session.query(Trade).filter_by(ticket=ticket).first()

    def log_risk_event(self, **event_data) -> None:
        """Log a risk management event."""
        with self.Session() as session:
            event = RiskEvent(**event_data)
            session.add(event)
            session.commit()

    def read_performance_report(self) -> Dict[str, Any]:
        """Generate a basic performance summary."""
        with self.Session() as session:
            trades = session.query(Trade).filter_by(status="CLOSED").all()
            if not trades:
                return {"total_trades": 0, "net_pnl": 0.0, "win_rate": 0.0}

            pnls = [t.pnl for t in trades]
            wins = [p for p in pnls if p > 0]

            return {
                "total_trades": len(trades),
                "net_pnl": sum(pnls),
                "win_rate": len(wins) / len(trades),
                "avg_trade": sum(pnls) / len(trades),
            }
