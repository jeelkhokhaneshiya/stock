from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum, JSON, Numeric
from sqlalchemy.sql import func
from app.db.base_class import Base
from app.models.enums import AssetType

class RiskApprovalRecord(Base):
    __tablename__ = "risk_approvals"

    id = Column(Integer, primary_key=True, index=True)
    decision_id = Column(Integer, nullable=True) # Optional link
    portfolio_id = Column(String, index=True, nullable=False)
    symbol = Column(String, index=True, nullable=False)
    asset_type = Column(SQLEnum(AssetType), nullable=False)
    original_decision = Column("decision", String, nullable=False)
    final_status = Column("status", String, nullable=False)
    execution_intent = Column(String, nullable=True)
    requested_amount = Column(Numeric(precision=18, scale=6), nullable=False)
    approved_amount = Column(Numeric(precision=18, scale=6), nullable=False)
    requested_quantity = Column(Numeric(precision=18, scale=6), nullable=False)
    approved_quantity = Column(Numeric(precision=18, scale=6), nullable=False)
    risk_profile = Column(String, nullable=False)
    analysis_score = Column(Float, nullable=True)
    risk_score = Column(Float, nullable=True)
    checks = Column(JSON, nullable=False)
    warnings = Column(JSON, nullable=False)
    rejection_reasons = Column(JSON, nullable=False)
    modifications = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
