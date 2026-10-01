from decimal import Decimal
import math
from typing import List, Dict, Any
from app.schemas.allocation import (
    AllocationPreviewRequest, PortfolioAllocationReport, 
    AllocationRecommendation, AllocationAction, PortfolioAnalysisReport
)
from app.services.analysis.service import InvestmentAnalysisService
from app.services.allocation.portfolio_analyzer import PortfolioAnalysisService
from app.services.allocation.diversification import DiversificationEngine
from app.services.allocation.position_sizing import PositionSizingEngine
from app.services.allocation.config import config
from app.schemas.allocation import PortfolioData
from app.models.enums import AssetType

class CapitalAllocationEngine:
    def __init__(self, analysis_service: InvestmentAnalysisService, p_analyzer: PortfolioAnalysisService):
        self.analysis_service = analysis_service
        self.p_analyzer = p_analyzer
        self.div_engine = DiversificationEngine()
        self.sizing_engine = PositionSizingEngine()

    def generate_preview(self, request: AllocationPreviewRequest, portfolio_id: str) -> PortfolioAllocationReport:
        # For preview, we assume empty existing portfolio if not passed, but we mock a Portfolio object here
        empty_portfolio = PortfolioData(id=portfolio_id, cash_balance=request.capital, currency="INR", holdings=[])
        
        current_portfolio = self.p_analyzer.analyze(empty_portfolio)
        limits = config.RISK_PROFILES[request.risk_profile]
        
        cash_reserve_pct = limits["MIN_CASH_RESERVE_PERCENT"]
        cash_reserve = request.capital * cash_reserve_pct
        allocatable_capital = request.capital - cash_reserve
        
        recommendations = []
        warnings = []
        
        remaining_capital = allocatable_capital
        
        # Analyze all candidates
        # To deterministic sort: we should really sort by score, but we process in order given.
        for cand in request.candidates:
            if remaining_capital <= Decimal("0"):
                break
                
            try:
                if cand.asset_type == AssetType.STOCK:
                    report = self.analysis_service.analyze_stock(cand.symbol)
                elif cand.asset_type == AssetType.ETF:
                    report = self.analysis_service.analyze_etf(cand.symbol)
                else:
                    report = self.analysis_service.analyze_mutual_fund(cand.symbol)
            except Exception as e:
                warnings.append(f"Failed to analyze {cand.symbol}: {e}")
                continue
                
            # Get current price
            try:
                quote = self.analysis_service.market_data_service.get_quote(cand.symbol)
                price = Decimal(str(quote.price))
            except:
                warnings.append(f"Could not get price for {cand.symbol}")
                continue
                
            # Size position
            sizing = self.sizing_engine.calculate_target(
                analysis=report,
                risk_profile=request.risk_profile,
                available_capital=request.capital,
                current_price=price
            )
            
            if sizing["rejected"]:
                recommendations.append(AllocationRecommendation(
                    symbol=cand.symbol,
                    asset_type=cand.asset_type,
                    action="REJECTED",
                    allocation_percent=Decimal("0"),
                    allocation_amount=Decimal("0"),
                    current_price=price,
                    recommended_quantity=Decimal("0"),
                    analysis_score=getattr(report, 'long_term_suitability_score', report.get('long_term_suitability_score', 0) if isinstance(report, dict) else 0),
                    risk_score=getattr(report, 'risk_score', report.get('risk_score', 0) if isinstance(report, dict) else 0) or 0.0,
                    confidence=getattr(report, 'analysis_confidence', report.get('analysis_confidence', 'INSUFFICIENT') if isinstance(report, dict) else 'INSUFFICIENT'),
                    reason=sizing["reason"]
                ))
                continue
                
            amount_to_allocate = sizing["amount"]
            
            # Bound by remaining allocatable capital
            if amount_to_allocate > remaining_capital:
                amount_to_allocate = remaining_capital
                if cand.asset_type != AssetType.MUTUAL_FUND:
                    qty = math.floor(amount_to_allocate / price)
                    amount_to_allocate = Decimal(str(qty)) * price
                
            if amount_to_allocate == Decimal("0"):
                continue
                
            # Check diversification
            div_check = self.div_engine.check_limits(
                symbol=cand.symbol,
                asset_type=cand.asset_type,
                sector="UNKNOWN",
                current_portfolio=current_portfolio,
                risk_profile=request.risk_profile,
                proposed_additional_amount=amount_to_allocate
            )
            
            if not div_check["allowed"]:
                warnings.append(f"Skipped {cand.symbol} due to diversification limits: {div_check['reason']}")
                continue
                
            qty = amount_to_allocate / price if cand.asset_type == AssetType.MUTUAL_FUND else Decimal(str(math.floor(amount_to_allocate/price)))
            
            if qty > 0:
                remaining_capital -= amount_to_allocate
                recommendations.append(AllocationRecommendation(
                    symbol=cand.symbol,
                    asset_type=cand.asset_type,
                    action="NEW_POSITION",
                    allocation_percent=amount_to_allocate / request.capital,
                    allocation_amount=amount_to_allocate,
                    current_price=price,
                    recommended_quantity=qty,
                    analysis_score=getattr(report, 'long_term_suitability_score', report.get('long_term_suitability_score', 0) if isinstance(report, dict) else 0),
                    risk_score=getattr(report, 'risk_score', report.get('risk_score', 0) if isinstance(report, dict) else 0) or 0.0,
                    confidence=getattr(report, 'analysis_confidence', report.get('analysis_confidence', 'INSUFFICIENT') if isinstance(report, dict) else 'INSUFFICIENT'),
                    reason=f"Allocated {amount_to_allocate} based on score {getattr(report, 'long_term_suitability_score', report.get('long_term_suitability_score', 0) if isinstance(report, dict) else 0):.1f} and risk profile {request.risk_profile}."
                ))
                
        return PortfolioAllocationReport(
            portfolio_id=portfolio_id,
            available_capital=request.capital,
            cash_reserve=cash_reserve,
            capital_available_for_allocation=allocatable_capital,
            recommendations=recommendations,
            unallocated_cash=remaining_capital,
            portfolio_risk="MODERATE", # Mocked for preview
            diversification_status="OK",
            warnings=warnings
        )
