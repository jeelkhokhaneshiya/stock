from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class PortfolioBase(BaseModel):
    name: str
    base_currency: str = "INR"

class PortfolioCreate(PortfolioBase):
    pass

class PortfolioResponse(PortfolioBase):
    id: int
    user_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
