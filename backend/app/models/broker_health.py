from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Float, Boolean
from sqlalchemy.sql import func
from app.db.base_class import Base

class BrokerSnapshot(Base):
    __tablename__ = "broker_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(String, index=True, nullable=False)
    broker = Column(String, nullable=False)
    captured_at = Column(DateTime(timezone=True), server_default=func.now())
    cash = Column(Float, nullable=False)
    holdings_count = Column(Integer, nullable=False)
    positions_count = Column(Integer, nullable=False)
    orders_count = Column(Integer, nullable=False)
    data_quality = Column(String, nullable=False)
    session_state = Column(String, nullable=False)

class OperationalEvent(Base):
    __tablename__ = "operational_events"
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(String, index=True, nullable=False)
    event = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    safe_message = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
