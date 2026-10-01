from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from app.models.enums import AssetType, OrderSide, OrderStatus

class PaperAccount(Base):
    __tablename__ = "paper_accounts"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, unique=True)
    initial_cash = Column(Float, nullable=False, default=100000.0)
    available_cash = Column(Float, nullable=False, default=100000.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    holdings = relationship("PaperHolding", back_populates="account", cascade="all, delete-orphan")
    orders = relationship("PaperOrder", back_populates="account", cascade="all, delete-orphan")


class PaperHolding(Base):
    __tablename__ = "paper_holdings"

    id = Column(Integer, primary_key=True, index=True)
    paper_account_id = Column(Integer, ForeignKey("paper_accounts.id"), nullable=False)
    symbol = Column(String, nullable=False, index=True)
    instrument_type = Column(SQLEnum(AssetType), nullable=False)
    quantity = Column(Float, nullable=False, default=0.0)
    average_price = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    account = relationship("PaperAccount", back_populates="holdings")


class PaperOrder(Base):
    __tablename__ = "paper_orders"

    id = Column(Integer, primary_key=True, index=True)
    paper_account_id = Column(Integer, ForeignKey("paper_accounts.id"), nullable=False)
    client_order_id = Column(String, nullable=False, unique=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    instrument_type = Column(SQLEnum(AssetType), nullable=False)
    side = Column(SQLEnum(OrderSide), nullable=False)
    quantity = Column(Float, nullable=False)
    requested_price = Column(Float, nullable=False)
    executed_price = Column(Float, nullable=True)
    status = Column(SQLEnum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    reject_reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    executed_at = Column(DateTime(timezone=True), nullable=True)

    account = relationship("PaperAccount", back_populates="orders")
