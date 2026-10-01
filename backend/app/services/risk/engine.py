from decimal import Decimal
import logging
from sqlalchemy.orm import Session
from app.schemas.risk import RiskApprovalRequest, RiskApprovalResult, RiskCheck, ApprovalStatus
from app.models.risk import RiskApprovalRecord
from app.services.allocation.config import config
from app.models.enums import AssetType

logger = logging.getLogger(__name__)

class RiskApprovalEngine:
    def __init__(self, db: Session):
        self.db = db

    def evaluate(self, request: RiskApprovalRequest) -> RiskApprovalResult:
        decision = request.decision
        status: ApprovalStatus = "APPROVED"
        execution_intent = None
        checks = []
        warnings = []
        rejection_reasons = []
        modifications = []
        
        req_amount = decision.recommended_amount
        req_qty = decision.recommended_quantity
        approved_amount = req_amount
        approved_qty = req_qty
        
        # AVOID and HOLD are non-execution actions
        if decision.decision in ["AVOID", "HOLD"]:
            return self._finalize_result(request, "NO_EXECUTION_REQUIRED", None, approved_amount, approved_qty, checks, warnings, rejection_reasons, modifications)
            
        # Hard Rule: Delivery Only
        if request.asset_type in [AssetType.STOCK, AssetType.ETF]:
            execution_intent = "DELIVERY_LONG_TERM"
            checks.append(RiskCheck(check="execution_intent", status="PASSED", message="Enforced DELIVERY_LONG_TERM"))
            
            if request.asset_type == AssetType.STOCK and approved_qty > 0 and approved_qty % 1 != 0:
                rejection_reasons.append("Stock purchases require whole shares")
                checks.append(RiskCheck(check="quantity_validity", status="FAILED", message="Fractional stocks not allowed"))
                status = "REJECTED"
        
        # Data Freshness
        if decision.decision in ["BUY", "ADD"]:
            if request.data_freshness_minutes > 15: # Arbitrary stale threshold
                rejection_reasons.append("Market data is stale")
                checks.append(RiskCheck(check="data_freshness", status="FAILED", message="Data older than 15 minutes"))
                status = "REJECTED"
            else:
                checks.append(RiskCheck(check="data_freshness", status="PASSED", message="Data is fresh"))
        
        # Price validation
        if decision.decision in ["BUY", "ADD"]:
            if request.current_price <= 0:
                rejection_reasons.append("Invalid current price")
                checks.append(RiskCheck(check="price_validity", status="FAILED", message="Price <= 0"))
                status = "REJECTED"
            
            if approved_qty <= 0:
                rejection_reasons.append("Approved quantity is <= 0")
                checks.append(RiskCheck(check="quantity_validity", status="FAILED", message="Quantity <= 0"))
                status = "REJECTED"

        # Analysis Confidence
        if decision.decision in ["BUY", "ADD"]:
            if request.analysis_confidence == "INSUFFICIENT":
                rejection_reasons.append("Insufficient analysis confidence for BUY/ADD")
                checks.append(RiskCheck(check="analysis_confidence", status="FAILED", message="Confidence is INSUFFICIENT"))
                status = "REJECTED"
            else:
                checks.append(RiskCheck(check="analysis_confidence", status="PASSED", message="Confidence is sufficient"))

        # Capital Safety
        if decision.decision in ["BUY", "ADD"]:
            if approved_amount > request.available_cash:
                rejection_reasons.append(f"Insufficient cash. Req: {approved_amount}, Avail: {request.available_cash}")
                checks.append(RiskCheck(check="capital_safety", status="FAILED", message="Exceeds available cash"))
                status = "REJECTED"
            else:
                checks.append(RiskCheck(check="capital_safety", status="PASSED", message="Within available cash bounds"))
                
        # Sell/Reduce Safety
        if decision.decision in ["SELL", "REDUCE"]:
            if request.current_quantity <= 0:
                rejection_reasons.append("Cannot SELL/REDUCE without existing holdings")
                checks.append(RiskCheck(check="holding_validation", status="FAILED", message="No holdings exist"))
                status = "REJECTED"
            elif approved_qty > request.current_quantity:
                rejection_reasons.append(f"Cannot sell more than held. Req: {approved_qty}, Held: {request.current_quantity}")
                checks.append(RiskCheck(check="holding_validation", status="FAILED", message="Excessive sell quantity"))
                status = "REJECTED"
            else:
                checks.append(RiskCheck(check="holding_validation", status="PASSED", message="Valid sell quantity"))

        # Position Concentration limit for BUY/ADD
        if decision.decision in ["BUY", "ADD"]:
            profile_config = config.RISK_PROFILES.get(request.risk_profile)
            if profile_config:
                max_pct = profile_config["MAX_SINGLE_STOCK_ALLOCATION"] * Decimal("100")
                if request.asset_type in [AssetType.ETF, AssetType.MUTUAL_FUND]:
                    max_pct = profile_config["MAX_SINGLE_ASSET_ALLOCATION"] * Decimal("100")
                
                projected_total_val = request.portfolio_total_value + approved_amount
                
                if projected_total_val > 0:
                    current_val = request.current_exposure
                    new_val = current_val + approved_amount
                    new_pct = (new_val / projected_total_val) * 100
                    
                    if new_pct > max_pct:
                        # Attempt modification
                        max_allowed_val = (max_pct / Decimal(100)) * projected_total_val
                        max_addable = max_allowed_val - current_val
                        
                        if max_addable > 0:
                            approved_amount = max_addable
                            # recalculate qty based on price
                            if request.current_price > 0:
                                if request.asset_type == AssetType.MUTUAL_FUND:
                                    approved_qty = approved_amount / request.current_price
                                else:
                                    import math
                                    approved_qty = Decimal(str(math.floor(approved_amount / request.current_price)))
                                    approved_amount = approved_qty * request.current_price
                                
                            if approved_qty <= 0:
                                status = "REJECTED"
                                rejection_reasons.append("Modification resulted in 0 quantity")
                                checks.append(RiskCheck(check="position_concentration", status="FAILED", message="Modification failed quantity bounds"))
                            else:
                                if status != "REJECTED":
                                    status = "MODIFIED"
                                    modifications.append(f"Amount reduced to {approved_amount} to respect concentration limit")
                                    checks.append(RiskCheck(check="position_concentration", status="WARNING", message="Modified to respect limit"))
                        else:
                            status = "REJECTED"
                            rejection_reasons.append("Position concentration limit exceeded. Cannot add more.")
                            checks.append(RiskCheck(check="position_concentration", status="FAILED", message="Exceeds concentration limit"))
                    else:
                        checks.append(RiskCheck(check="position_concentration", status="PASSED", message="Within concentration bounds"))
            else:
                checks.append(RiskCheck(check="risk_profile", status="FAILED", message="Unknown risk profile"))
                status = "REJECTED"

        if status == "REJECTED":
            approved_amount = Decimal(0)
            approved_qty = Decimal(0)

        return self._finalize_result(request, status, execution_intent, approved_amount, approved_qty, checks, warnings, rejection_reasons, modifications)
        
    def _finalize_result(self, request, status, execution_intent, app_amt, app_qty, checks, warnings, rejection_reasons, modifications) -> RiskApprovalResult:
        result = RiskApprovalResult(
            status=status,
            decision=request.decision.decision,
            execution_intent=execution_intent,
            requested_amount=request.decision.recommended_amount,
            approved_amount=app_amt,
            requested_quantity=request.decision.recommended_quantity,
            approved_quantity=app_qty,
            checks=checks,
            warnings=warnings,
            rejection_reasons=rejection_reasons,
            modifications=modifications
        )
        
        record = RiskApprovalRecord(
            portfolio_id=request.portfolio_id,
            symbol=request.symbol,
            asset_type=request.asset_type,
            original_decision=request.decision.decision,
            final_status=status,
            execution_intent=execution_intent,
            requested_amount=request.decision.recommended_amount,
            approved_amount=app_amt,
            requested_quantity=request.decision.recommended_quantity,
            approved_quantity=app_qty,
            risk_profile=request.risk_profile,
            analysis_score=0.0,
            risk_score=0.0,
            checks=[c.model_dump() for c in checks],
            warnings=warnings,
            rejection_reasons=rejection_reasons,
            modifications=modifications
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        result.id = record.id
        return result
