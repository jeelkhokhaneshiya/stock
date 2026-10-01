from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Numeric
from sqlalchemy.sql import func
from app.db.base_class import Base
from app.models.enums import OrderSide, ExecutionStatus, ExecutionMode

class ShadowOrderRecord(Base):
    __tablename__ = "shadow_orders"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    decision_id = Column(Integer, ForeignKey("decisions.id"), nullable=False)
    risk_approval_id = Column(Integer, ForeignKey("risk_approvals.id"), nullable=True)
    
    symbol = Column(String, index=True, nullable=False)
    isin = Column(String, nullable=True)
    side = Column(SQLEnum(OrderSide), nullable=False)
    
    quantity = Column(Numeric(precision=18, scale=6), nullable=False)
    requested_amount = Column(Numeric(precision=18, scale=6), nullable=False)
    
    simulated_fill_quantity = Column(Numeric(precision=18, scale=6), nullable=True)
    simulated_fill_price = Column(Numeric(precision=18, scale=6), nullable=True)
    
    status = Column(SQLEnum(ExecutionStatus), nullable=False, default=ExecutionStatus.PENDING)
    execution_mode = Column(SQLEnum(ExecutionMode), nullable=False, default=ExecutionMode.SHADOW)
    
    reason = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Market Price Snapshot fields
    market_price = Column(Numeric(precision=18, scale=6), nullable=True)
    data_provider = Column(String, nullable=True)
    data_freshness_seconds = Column(Integer, nullable=True)
