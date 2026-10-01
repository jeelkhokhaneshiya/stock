from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.db.base_class import Base

class ExecutionReadinessRecord(Base):
    __tablename__ = "execution_readiness_checks"

    id = Column(Integer, primary_key=True, index=True)
    decision_id = Column(Integer, nullable=False, index=True)
    risk_approval_id = Column(Integer, nullable=True)
    portfolio_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    
    mode = Column(String, nullable=False)
    checks = Column(JSON, nullable=False)
    blocking_reasons = Column(JSON, nullable=False)
    warnings = Column(JSON, nullable=False)
    result = Column(String, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
