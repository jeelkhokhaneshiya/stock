from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime
from app.models.enums import AssetType

ConfidenceLevel = Literal["HIGH", "MEDIUM", "LOW", "INSUFFICIENT"]
SuitabilityCategory = Literal["VERY_STRONG", "STRONG", "MODERATE", "WEAK", "VERY_WEAK"]

class AnalysisReport(BaseModel):
    symbol: str
    asset_type: AssetType
    analysis_timestamp: datetime
    long_term_suitability_score: float = Field(..., ge=0, le=100)
    category: SuitabilityCategory
    analysis_confidence: ConfidenceLevel

    fundamental_score: Optional[float] = None
    technical_score: Optional[float] = None
    valuation_score: Optional[float] = None
    quality_score: Optional[float] = None
    risk_score: Optional[float] = None

    strengths: List[str] = []
    risks: List[str] = []
    missing_data: List[str] = []
    
    explanation: str

class ComponentScore(BaseModel):
    score: float
    weight: float
    is_available: bool
    explanation: str
