from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, DECIMAL
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base_class import Base
from app.models.enums import BrokerOrderStatus, OrderSide, ExecutionIntent

class BrokerOrderRecord(Base):
    __tablename__ = "broker_orders"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    client_order_id = Column(String, unique=True, index=True, nullable=False)
    broker_order_id = Column(String, nullable=True, index=True)
    
    symbol = Column(String, nullable=False)
    isin = Column(String, nullable=True)
    exchange = Column(String, nullable=False)
    side = Column(Enum(OrderSide), nullable=False)
    
    quantity = Column(DECIMAL, nullable=False)
    requested_quantity = Column(DECIMAL, nullable=False)
    executed_quantity = Column(DECIMAL, default=0.0)
    remaining_quantity = Column(DECIMAL, nullable=False)
    
    price = Column(DECIMAL, nullable=True)
    average_fill_price = Column(DECIMAL, nullable=True)
    
    order_type = Column(String, nullable=False)
    product = Column(String, nullable=False)
    execution_intent = Column(Enum(ExecutionIntent), nullable=False)
    
    status = Column(Enum(BrokerOrderStatus), default=BrokerOrderStatus.CREATED, nullable=False)
    broker = Column(String, nullable=False)
    
    submitted_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    
    error_code = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    
    # Traceability fields
    decision_id = Column(Integer, nullable=True)
    risk_approval_id = Column(Integer, nullable=True)

    portfolio = relationship("Portfolio")
    user = relationship("User")
