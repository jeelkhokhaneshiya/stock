from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from decimal import Decimal
import logging
from app.models.portfolio import Portfolio
from app.models.autonomous import AutonomousCycleRecord
from app.models.enums import CycleStatus, ExecutionIntent, DecisionAction
from app.models.paper import PaperAccount
from app.models.execution import ExecutionRecord
from app.services.execution_service import ExecutionService
from app.schemas.autonomous import AutonomousCycleResult
from app.services.market_session import MarketSessionService
from app.services.universe_provider import InvestmentUniverseProvider

logger = logging.getLogger(__name__)

class AutonomousPortfolioManager:
    def __init__(
        self,
        db: Session,
        market_session: MarketSessionService,
        universe_provider: InvestmentUniverseProvider,
        market_data_service: Any,
        investment_analysis: Any,
        portfolio_analysis: Any,
        capital_allocation: Any,
        ai_decision: Any,
        risk_approval: Any,
        execution_service: ExecutionService,
    ):
        self.db = db
        self.market_session = market_session
        self.universe_provider = universe_provider
        self.market_data_service = market_data_service
        self.investment_analysis = investment_analysis
        self.portfolio_analysis = portfolio_analysis
        self.capital_allocation = capital_allocation
        self.ai_decision = ai_decision
        self.risk_approval = risk_approval
        self.execution_service = execution_service

    def execute_cycle(self, portfolio_id: str) -> AutonomousCycleResult:
        # Prevent concurrent cycles
        existing_cycle = self.db.query(AutonomousCycleRecord).filter(
            AutonomousCycleRecord.portfolio_id == portfolio_id,
            AutonomousCycleRecord.status == CycleStatus.RUNNING
        ).first()
        
        if existing_cycle:
            return AutonomousCycleResult(
                cycle_id=existing_cycle.id,
                portfolio_id=portfolio_id,
                status=CycleStatus.FAILED,
                market_status="UNKNOWN",
                errors=["CYCLE_ALREADY_RUNNING"]
            )

        cycle = AutonomousCycleRecord(portfolio_id=portfolio_id, status=CycleStatus.RUNNING)
        self.db.add(cycle)
        self.db.commit()
        
        result = AutonomousCycleResult(
            cycle_id=cycle.id,
            portfolio_id=portfolio_id,
            status=CycleStatus.RUNNING,
            market_status="UNKNOWN"
        )

        try:
            # 1 & 2. Check market session
            market_status = self.market_session.get_market_status()
            result.market_status = market_status
            if market_status == "MARKET_CLOSED":
                cycle.status = CycleStatus.COMPLETED
                result.status = CycleStatus.COMPLETED
                result.warnings.append("NO_EXECUTION_MARKET_CLOSED")
                self.db.commit()
                return result

            # 3. Load portfolio and cash
            portfolio = self.db.query(Portfolio).filter(Portfolio.id == int(portfolio_id)).first()
            if not portfolio:
                raise ValueError("Portfolio not found")

            # 4. Discover candidates
            candidates = self.universe_provider.get_candidates()
            cycle.candidate_count = len(candidates)
            result.candidate_count = len(candidates)

            for candidate in candidates:
                try:
                    self._process_candidate(candidate, int(portfolio_id), cycle, result)
                except Exception as e:
                    logger.error(f"Error processing candidate {candidate}: {e}")
                    result.errors.append(f"Candidate {candidate.get('symbol')} failed: {str(e)}")
                    cycle.error_count += 1
                    result.failed_count += 1
                    
            if result.failed_count == len(candidates) and len(candidates) > 0:
                cycle.status = CycleStatus.FAILED
                result.status = CycleStatus.FAILED
            elif result.failed_count > 0:
                cycle.status = CycleStatus.PARTIAL
                result.status = CycleStatus.PARTIAL
            else:
                cycle.status = CycleStatus.COMPLETED
                result.status = CycleStatus.COMPLETED

        except Exception as e:
            logger.error(f"Cycle failed: {e}")
            cycle.status = CycleStatus.FAILED
            result.status = CycleStatus.FAILED
            result.errors.append(str(e))
            cycle.error_count += 1
            
        cycle.summary = result.model_dump()
        self.db.commit()
        return result

    def _process_candidate(self, candidate: Dict, portfolio_id: int, cycle: AutonomousCycleRecord, result: AutonomousCycleResult):
        symbol = candidate["symbol"]
        
        # Check available cash logic implicitly done in capital allocation, but we must use fresh portfolio state
        # 8 & 9 & 10. Run analyses and allocation
        # We need mockable calls here. Since the user asked to just conceptualize the pipeline and use injected dependencies:
        
        # A) Market Data
        market_data = self.market_data_service.get_market_data(symbol)
        
        # B) Investment Analysis
        analysis_report = self.investment_analysis.analyze(symbol, market_data)
        cycle.analysis_count += 1
        result.analysis_count += 1
        
        # C) Portfolio Analysis
        portfolio_state = self.portfolio_analysis.analyze(str(portfolio_id))
        
        # D) Capital Allocation
        allocation = self.capital_allocation.allocate(str(portfolio_id), symbol, analysis_report, portfolio_state)
        
        # E) AI Decision
        decision = self.ai_decision.generate_decision(str(portfolio_id), symbol, analysis_report, allocation)
        cycle.decision_count += 1
        result.decision_count += 1
        
        if decision.decision in [DecisionAction.HOLD.value, DecisionAction.AVOID.value]:
            result.warnings.append(f"{symbol}: NO_EXECUTION_REQUIRED ({decision.decision})")
            return
            
        # Check duplicate
        existing_exec = self.db.query(ExecutionRecord).filter(
            ExecutionRecord.decision_id == decision.id
        ).first()
        if existing_exec:
            result.warnings.append(f"{symbol}: DUPLICATE_SKIPPED")
            return

        # F) Risk Approval
        approval = self.risk_approval.evaluate(decision)
        if approval.final_status == "REJECTED":
            cycle.rejected_count += 1
            result.rejected_count += 1
            result.warnings.append(f"{symbol}: REJECTED by Risk Engine")
            return
        elif approval.final_status == "MODIFIED":
            cycle.modified_count += 1
            result.modified_count += 1
        else:
            cycle.approved_count += 1
            result.approved_count += 1

        # G) Execution
        exec_record = self.execution_service.execute_approved_decision(approval.id)
        cycle.executed_count += 1
        result.executed_count += 1
        result.execution_ids.append(exec_record.id)
        
        if exec_record.side == "BUY":
            result.total_buy_amount += float(exec_record.executed_amount)
        else:
            result.total_sell_amount += float(exec_record.executed_amount)

        # H) Portfolio Refresh is automatic because next candidate's portfolio_analysis.analyze() 
        # fetches from DB. But we should flush.
        self.db.flush()
