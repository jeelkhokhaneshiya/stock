from datetime import datetime, timezone
from decimal import Decimal
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.decision import DecisionRecord
from app.models.risk import RiskApprovalRecord
from app.models.reconciliation import ReconciliationRun, ReconciliationItem
from app.models.execution_readiness import ExecutionReadinessRecord
from app.models.shadow import ShadowOrderRecord
from app.models.enums import ReconciliationSeverity, ExecutionMode
from app.services.safety_monitor import SafetyMonitor, SafetyStatus

class ExecutionReadinessResult(BaseModel):
    approved: bool
    mode: str
    checks: Dict[str, bool]
    warnings: List[str]
    blocking_reasons: List[str]
    decision_id: int
    risk_approval_id: Optional[int] = None
    reconciliation_id: Optional[int] = None
    timestamp: str

class ExecutionReadinessService:
    def __init__(self, db: Session):
        self.db = db
        self.safety_monitor = SafetyMonitor()

    def evaluate_readiness(
        self, 
        user_id: str,
        portfolio_id: str,
        decision_id: int,
        market_price: Decimal,
        data_provider: str,
        data_age_seconds: int,
        available_cash: Decimal,
        current_holdings: Dict[str, Decimal]
    ) -> ExecutionReadinessResult:
        
        checks = {}
        blocking_reasons = []
        warnings = []
        
        decision = self.db.query(DecisionRecord).filter(DecisionRecord.id == decision_id).first()
        risk_approval = self.db.query(RiskApprovalRecord).filter(RiskApprovalRecord.decision_id == decision_id).first()
        latest_recon = self.db.query(ReconciliationRun).filter(ReconciliationRun.portfolio_id == portfolio_id).order_by(ReconciliationRun.id.desc()).first()
        
        # 14. decision exists
        checks["decision_exists"] = decision is not None
        if not decision:
            blocking_reasons.append("DECISION_NOT_FOUND")
            return self._finalize_result(user_id, portfolio_id, decision_id, None, None, checks, warnings, blocking_reasons)
            
        # 15. decision belongs to same portfolio
        checks["decision_portfolio_match"] = decision.portfolio_id == portfolio_id
        if decision.portfolio_id != portfolio_id:
            blocking_reasons.append("DECISION_PORTFOLIO_MISMATCH")

        # 5. decision expiration
        now = datetime.now(timezone.utc)
        decision_age = (now - decision.created_at.replace(tzinfo=timezone.utc)).total_seconds()
        checks["decision_fresh"] = decision_age <= settings.DECISION_MAX_AGE_SECONDS
        if not checks["decision_fresh"]:
            blocking_reasons.append("DECISION_EXPIRED")
            
        # 12. risk approval exists
        checks["risk_approval_exists"] = risk_approval is not None
        if not risk_approval:
            blocking_reasons.append("RISK_APPROVAL_MISSING")
            
        # 13. risk approval still valid
        if risk_approval:
            approval_age = (now - risk_approval.created_at.replace(tzinfo=timezone.utc)).total_seconds()
            checks["risk_approval_fresh"] = approval_age <= settings.RISK_APPROVAL_MAX_AGE_SECONDS
            if not checks["risk_approval_fresh"]:
                blocking_reasons.append("RISK_APPROVAL_EXPIRED")
                
        # 7. market data freshness
        checks["market_data_fresh"] = data_age_seconds <= settings.QUOTE_MAX_AGE_SECONDS
        if not checks["market_data_fresh"]:
            blocking_reasons.append("STALE_MARKET_DATA")
            
        # 4. Reconciliation safety
        if latest_recon:
            recon_items = self.db.query(ReconciliationItem).filter(ReconciliationItem.run_id == latest_recon.id).all()
            has_critical = any(item.severity == ReconciliationSeverity.CRITICAL for item in recon_items)
            has_unsupported = any(item.status == "UNSUPPORTED_BROKER_POSITION" for item in recon_items) # string for simplicity
            
            checks["reconciliation_safe"] = not has_critical and not has_unsupported
            if not checks["reconciliation_safe"]:
                blocking_reasons.append("CRITICAL_RECONCILIATION_ISSUE")
        else:
            checks["reconciliation_safe"] = True
            
        # 8. Fundamental + Technical Analysis requirement
        if decision.asset_type.value == "STOCK" and decision.decision in ["BUY", "ADD"]:
            # mock check: ensure some analysis was done (we check if confidence is sufficient)
            checks["sufficient_analysis"] = decision.confidence >= 0.7
            if not checks["sufficient_analysis"]:
                blocking_reasons.append("INSUFFICIENT_ANALYTICAL_COVERAGE")
        else:
            checks["sufficient_analysis"] = True
            
        # 10. & 11. Sufficient cash/holdings
        if decision.decision in ["BUY", "ADD"] and risk_approval:
            checks["sufficient_cash"] = available_cash >= risk_approval.approved_amount
            if not checks["sufficient_cash"]:
                blocking_reasons.append("INSUFFICIENT_CASH")
        elif decision.decision in ["SELL", "REDUCE"] and risk_approval:
            current_qty = current_holdings.get(decision.symbol, Decimal("0"))
            checks["sufficient_holdings"] = current_qty >= risk_approval.approved_quantity
            if not checks["sufficient_holdings"]:
                blocking_reasons.append("INSUFFICIENT_HOLDINGS")
        else:
            checks["sufficient_cash"] = True
            checks["sufficient_holdings"] = True

        # 9. DELIVERY_LONG_TERM intent
        if risk_approval:
            checks["valid_intent"] = risk_approval.execution_intent == "DELIVERY_LONG_TERM"
            if not checks["valid_intent"]:
                blocking_reasons.append("INVALID_EXECUTION_INTENT")
                
        # 11. duplicate order / 12. idempotent execution
        existing_shadow = self.db.query(ShadowOrderRecord).filter(ShadowOrderRecord.decision_id == decision.id).first()
        checks["not_duplicate"] = existing_shadow is None
        if existing_shadow:
            blocking_reasons.append("DECISION_ALREADY_EXECUTED")
            
        # 13. & 14. Safety Monitor, Live Lock, Kill switch
        safety_res = self.safety_monitor.check_safety(portfolio_id)
        checks["safety_monitor_safe"] = safety_res["status"] == SafetyStatus.SAFE
        if not checks["safety_monitor_safe"]:
            blocking_reasons.extend(safety_res.get("reasons", []))
            
        return self._finalize_result(user_id, portfolio_id, decision_id, 
                                     risk_approval.id if risk_approval else None, 
                                     latest_recon.id if latest_recon else None,
                                     checks, warnings, blocking_reasons)

    def _finalize_result(self, user_id, portfolio_id, decision_id, risk_approval_id, reconciliation_id, checks, warnings, blocking_reasons):
        if settings.EXECUTION_MODE == "LIVE" and not settings.LIVE_EXECUTION_UNLOCKED:
            mode = "LIVE_DISABLED"
            blocking_reasons.append("LIVE_EXECUTION_NOT_UNLOCKED")
        elif len(blocking_reasons) > 0:
            mode = "BLOCKED"
        elif settings.EXECUTION_MODE == "PAPER":
            mode = "READY_FOR_PAPER"
        elif settings.EXECUTION_MODE == "SHADOW":
            mode = "READY_FOR_SHADOW"
        else:
            mode = "BLOCKED"
            blocking_reasons.append("UNKNOWN_EXECUTION_MODE")
            
        res = ExecutionReadinessResult(
            approved=len(blocking_reasons) == 0,
            mode=mode,
            checks=checks,
            warnings=warnings,
            blocking_reasons=blocking_reasons,
            decision_id=decision_id,
            risk_approval_id=risk_approval_id,
            reconciliation_id=reconciliation_id,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        record = ExecutionReadinessRecord(
            decision_id=decision_id,
            risk_approval_id=risk_approval_id,
            portfolio_id=portfolio_id,
            user_id=user_id,
            mode=mode,
            checks=checks,
            blocking_reasons=blocking_reasons,
            warnings=warnings,
            result="APPROVED" if res.approved else "BLOCKED"
        )
        self.db.add(record)
        self.db.commit()
        
        return res
