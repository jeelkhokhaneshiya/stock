from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum as SQLEnum, JSON, Numeric
from sqlalchemy.sql import func
from app.db.base_class import Base
from app.models.enums import AssetType, OrderSide, ExecutionIntent, ExecutionStatus

class ExecutionRecord(Base):
    __tablename__ = "executions"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(String, index=True, nullable=False)
    decision_id = Column(Integer, index=True, nullable=True)
    risk_approval_id = Column(Integer, index=True, nullable=True)
    symbol = Column(String, index=True, nullable=False)
    asset_type = Column(SQLEnum(AssetType), nullable=False)
    side = Column(SQLEnum(OrderSide), nullable=False)
    execution_intent = Column(SQLEnum(ExecutionIntent), nullable=False)
    
    requested_quantity = Column(Numeric(precision=18, scale=6), nullable=False)
    approved_quantity = Column(Numeric(precision=18, scale=6), nullable=False)
    executed_quantity = Column(Numeric(precision=18, scale=6), nullable=False, default=0)
    
    requested_amount = Column(Numeric(precision=18, scale=6), nullable=False)
    approved_amount = Column(Numeric(precision=18, scale=6), nullable=False)
    executed_amount = Column(Numeric(precision=18, scale=6), nullable=False, default=0)
    
    price = Column(Numeric(precision=18, scale=6), nullable=True)
    status = Column(SQLEnum(ExecutionStatus), nullable=False, default=ExecutionStatus.PENDING)
    
    broker_order_id = Column(String, nullable=True, index=True)
    error_message = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
