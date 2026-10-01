from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base_class import Base
from app.models.user import User

class Watchlist(Base):
    __tablename__ = "watchlist"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    symbol = Column(String, index=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(String, nullable=True)

class InvestmentRecommendation(Base):
    __tablename__ = "investment_recommendation"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    decision = Column(String)  # BUY, HOLD, SELL, WATCHLIST, AVOID
    confidence = Column(Float)
    investment_score = Column(Float)
    risk_level = Column(String)
    reasons = Column(JSON)
    warnings = Column(JSON)
    data_freshness = Column(String)
    review_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class PaperPortfolio(Base):
    __tablename__ = "paper_portfolio"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    cash = Column(Float, default=1000000.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
class PaperPosition(Base):
    __tablename__ = "paper_position"
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("paper_portfolio.id"))
    symbol = Column(String, index=True)
    quantity = Column(Integer)
    average_price = Column(Float)
    current_price = Column(Float, nullable=True)

class PaperTrade(Base):
    __tablename__ = "paper_trade"
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("paper_portfolio.id"))
    symbol = Column(String, index=True)
    side = Column(String) # BUY / SELL
    quantity = Column(Integer)
    price = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    reason = Column(String, nullable=True)