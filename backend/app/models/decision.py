from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum, JSON, Numeric
from sqlalchemy.sql import func
from app.db.base_class import Base
from app.models.enums import AssetType

class DecisionRecord(Base):
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(String, index=True, nullable=False)
    symbol = Column(String, index=True, nullable=False)
    asset_type = Column(SQLEnum(AssetType), nullable=False)
    decision = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)
    analysis_score = Column(Float, nullable=False)
    allocation_amount = Column(Numeric(precision=18, scale=6), nullable=False)
    allocation_percent = Column(Numeric(precision=5, scale=2), nullable=False)
    recommended_quantity = Column(Numeric(precision=18, scale=6), nullable=False)
    reason = Column(String, nullable=False)
    supporting_factors = Column(JSON, nullable=False)
    risk_factors = Column(JSON, nullable=False)
    reassessment_conditions = Column(JSON, nullable=False)
    prompt_version = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
