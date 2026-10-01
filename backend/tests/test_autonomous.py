import pytest
from unittest.mock import MagicMock
from app.services.autonomous_manager import AutonomousPortfolioManager
from app.services.market_session import MarketSessionService
from app.services.universe_provider import MockInvestmentUniverseProvider
from app.models.enums import CycleStatus
from app.models.portfolio import Portfolio
from app.models.paper import PaperAccount

@pytest.fixture
def autonomous_manager(db_session):
    market_session = MarketSessionService()
    market_session.set_override("MARKET_OPEN")
    
    universe_provider = MockInvestmentUniverseProvider([{"symbol": "RELIANCE", "type": "STOCK"}])
    
    market_data = MagicMock()
    market_data.get_market_data.return_value = {"price": 2500.0}
    
    inv_analysis = MagicMock()
    inv_analysis.analyze.return_value = {"score": 85}
    
    port_analysis = MagicMock()
    port_analysis.analyze.return_value = {"cash": 10000}
    
    cap_alloc = MagicMock()
    cap_alloc.allocate.return_value = {"recommended_amount": 5000}
    
    ai_decision = MagicMock()
    decision_mock = MagicMock()
    decision_mock.id = 1
    decision_mock.decision = "BUY"
    ai_decision.generate_decision.return_value = decision_mock
    
    risk_approval = MagicMock()
    approval_mock = MagicMock()
    approval_mock.id = 1
    approval_mock.final_status = "APPROVED"
    risk_approval.evaluate.return_value = approval_mock
    
    exec_service = MagicMock()
    exec_record = MagicMock()
    exec_record.id = 1
    exec_record.side = "BUY"
    exec_record.executed_amount = 5000
    exec_service.execute_approved_decision.return_value = exec_record

    return AutonomousPortfolioManager(
        db=db_session,
        market_session=market_session,
        universe_provider=universe_provider,
        market_data_service=market_data,
        investment_analysis=inv_analysis,
        portfolio_analysis=port_analysis,
        capital_allocation=cap_alloc,
        ai_decision=ai_decision,
        risk_approval=risk_approval,
        execution_service=exec_service
    )

from app.models.user import User



def test_autonomous_cycle_market_closed(autonomous_manager, db_session, test_user):
    # Setup portfolio
    portfolio = Portfolio(id=1, name="Test", user_id=test_user.id)
    db_session.add(portfolio)
    db_session.commit()

    autonomous_manager.market_session.set_override("MARKET_CLOSED")
    result = autonomous_manager.execute_cycle("1")
    
    assert result.status == CycleStatus.COMPLETED
    assert result.market_status == "MARKET_CLOSED"
    assert "NO_EXECUTION_MARKET_CLOSED" in result.warnings

def test_autonomous_cycle_success(autonomous_manager, db_session, test_user):
    portfolio = Portfolio(id=2, name="Test 2", user_id=test_user.id)
    db_session.add(portfolio)
    db_session.commit()
    
    result = autonomous_manager.execute_cycle("2")
    
    assert result.status == CycleStatus.COMPLETED
    assert result.candidate_count == 1
    assert result.approved_count == 1
    assert result.executed_count == 1
    assert result.total_buy_amount == 5000

def test_autonomous_cycle_already_running(autonomous_manager, db_session, test_user):
    from app.models.autonomous import AutonomousCycleRecord
    portfolio = Portfolio(id=3, name="Test 3", user_id=test_user.id)
    db_session.add(portfolio)
    
    # Simulate existing running cycle
    running_cycle = AutonomousCycleRecord(portfolio_id="3", status=CycleStatus.RUNNING)
    db_session.add(running_cycle)
    db_session.commit()
    
    result = autonomous_manager.execute_cycle("3")
    assert result.status == CycleStatus.FAILED
    assert "CYCLE_ALREADY_RUNNING" in result.errors
