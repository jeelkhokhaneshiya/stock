from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, DECIMAL
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base_class import Base
from app.models.enums import ReconciliationStatus, ReconciliationSeverity

class ReconciliationRun(Base):
    __tablename__ = "reconciliation_runs"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    broker = Column(String, nullable=False)
    status = Column(Enum(ReconciliationStatus), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    items = relationship("ReconciliationItem", back_populates="run", cascade="all, delete-orphan")
    portfolio = relationship("Portfolio")

class ReconciliationItem(Base):
    __tablename__ = "reconciliation_items"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("reconciliation_runs.id"), nullable=False, index=True)
    
    status = Column(Enum(ReconciliationStatus), nullable=False)
    severity = Column(Enum(ReconciliationSeverity), nullable=False)
    
    symbol = Column(String, nullable=True)
    isin = Column(String, nullable=True)
    exchange = Column(String, nullable=True)
    
    broker_quantity = Column(DECIMAL, nullable=True)
    internal_quantity = Column(DECIMAL, nullable=True)
    quantity_difference = Column(DECIMAL, nullable=True)
    
    broker_average_price = Column(DECIMAL, nullable=True)
    internal_average_price = Column(DECIMAL, nullable=True)
    price_difference = Column(DECIMAL, nullable=True)
    
    reason = Column(String, nullable=True)
    
    run = relationship("ReconciliationRun", back_populates="items")
