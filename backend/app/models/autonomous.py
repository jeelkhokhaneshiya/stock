from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, JSON, ForeignKey
from sqlalchemy.sql import func
from app.db.base_class import Base
from app.models.enums import CycleStatus

class AutonomousCycleRecord(Base):
    __tablename__ = "autonomous_cycles"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(String, index=True, nullable=False)
    status = Column(SQLEnum(CycleStatus), nullable=False, default=CycleStatus.RUNNING)
    
    candidate_count = Column(Integer, nullable=False, default=0)
    analysis_count = Column(Integer, nullable=False, default=0)
    decision_count = Column(Integer, nullable=False, default=0)
    approved_count = Column(Integer, nullable=False, default=0)
    modified_count = Column(Integer, nullable=False, default=0)
    rejected_count = Column(Integer, nullable=False, default=0)
    executed_count = Column(Integer, nullable=False, default=0)
    error_count = Column(Integer, nullable=False, default=0)
    
    summary = Column(JSON, nullable=True)
    
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
