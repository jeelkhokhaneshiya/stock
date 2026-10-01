from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.shadow import ShadowOrderRecord
from app.models.enums import OrderSide, ExecutionStatus, ExecutionMode
from app.core.config import settings

class ShadowExecutionService:
    def __init__(self, db: Session):
        self.db = db

    def execute_shadow_order(self, portfolio_id: str, user_id: str, decision_id: int, 
                             symbol: str, side: OrderSide, quantity: Decimal, requested_amount: Decimal,
                             market_price: Decimal, data_provider: str = "mock", data_freshness_seconds: int = 0,
                             risk_approval_id: int = None) -> ShadowOrderRecord:
        
        # Stale data check
        if data_freshness_seconds > settings.QUOTE_MAX_AGE_SECONDS:
            raise ValueError("SHADOW_EXECUTION_BLOCKED_STALE_DATA")
            
        # Create record
        order = ShadowOrderRecord(
            portfolio_id=portfolio_id,
            user_id=user_id,
            decision_id=decision_id,
            risk_approval_id=risk_approval_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            requested_amount=requested_amount,
            market_price=market_price,
            data_provider=data_provider,
            data_freshness_seconds=data_freshness_seconds,
            status=ExecutionStatus.PENDING,
            execution_mode=ExecutionMode.SHADOW,
        )
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        
        # Simulate full fill
        order.simulated_fill_quantity = quantity
        order.simulated_fill_price = market_price
        order.status = ExecutionStatus.EXECUTED
        order.completed_at = datetime.now(timezone.utc)
        order.reason = "Simulated FULL fill in SHADOW mode"
        
        self.db.commit()
        self.db.refresh(order)
        return order
