import pytest
from decimal import Decimal
from app.services.execution_service import ExecutionService
from app.schemas.broker import BrokerOrderRequest
from app.models.enums import OrderSide, ExecutionIntent, BrokerOrderStatus
from app.models.broker_order import BrokerOrderRecord
from app.models.paper import PaperAccount, PaperHolding
from app.core.config import settings
import uuid

@pytest.fixture
def exec_service(db_session, test_user):
    return ExecutionService(db_session, test_user.id)

def test_critical_real_money_safety(exec_service, monkeypatch, test_portfolio):
    monkeypatch.setattr(settings, "BROKER_PROVIDER", "angel_one")
    monkeypatch.setattr(settings, "ENABLE_LIVE_TRADING", "false")
    
    req = BrokerOrderRequest(
        client_order_id=f"TEST-{uuid.uuid4().hex[:6]}",
        symbol="RELIANCE",
        exchange="NSE",
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        order_type="MARKET",
        product="DELIVERY",
        execution_intent=ExecutionIntent.DELIVERY_LONG_TERM,
        portfolio_id=test_portfolio.id
    )
    
    with pytest.raises(ValueError, match="LIVE_TRADING_DISABLED"):
        exec_service.submit_order(req)
        
    req.side = OrderSide.SELL
    req.client_order_id = f"TEST-{uuid.uuid4().hex[:6]}"
    with pytest.raises(ValueError, match="LIVE_TRADING_DISABLED"):
        exec_service.submit_order(req)

def test_critical_duplicate_idempotency(exec_service, monkeypatch, test_portfolio, db_session):
    monkeypatch.setattr(settings, "BROKER_PROVIDER", "mock_broker")
    
    acc = PaperAccount(portfolio_id=test_portfolio.id, available_cash=10000.0, initial_cash=10000.0)
    db_session.add(acc)
    db_session.commit()
    
    req = BrokerOrderRequest(
        client_order_id="TEST-123",
        symbol="TCS",
        exchange="NSE",
        side=OrderSide.BUY,
        quantity=Decimal("5"),
        order_type="MARKET",
        product="DELIVERY",
        execution_intent=ExecutionIntent.DELIVERY_LONG_TERM,
        portfolio_id=test_portfolio.id
    )
    
    # First submit should succeed
    record1 = exec_service.submit_order(req)
    assert record1.status == BrokerOrderStatus.OPEN
    
    # Second submit should fail
    with pytest.raises(ValueError, match="DUPLICATE_ORDER"):
        exec_service.submit_order(req)

def test_mock_angel_execution_partial_fill(exec_service, monkeypatch, test_portfolio, db_session):
    monkeypatch.setattr(settings, "BROKER_PROVIDER", "mock_broker")
    
    acc = PaperAccount(portfolio_id=test_portfolio.id, available_cash=10000.0, initial_cash=10000.0)
    db_session.add(acc)
    db_session.commit()
    
    req = BrokerOrderRequest(
        client_order_id=f"TEST-{uuid.uuid4().hex[:6]}",
        symbol="INFY",
        exchange="NSE",
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        order_type="MARKET",
        product="DELIVERY",
        execution_intent=ExecutionIntent.DELIVERY_LONG_TERM,
        portfolio_id=test_portfolio.id
    )
    
    # Inject simulation mode manually since exec_service instantiates it locally
    # We can patch it.
    from app.services.brokers.angel_one.mock_execution import MockAngelOneExecutionAdapter
    original_adapter = MockAngelOneExecutionAdapter
    
    class TestMockAdapter(original_adapter):
        def __init__(self):
            super().__init__()
            self.simulation_mode = "PARTIAL_FILL"
            self.partial_fill_amount = Decimal("6")
            
    with monkeypatch.context() as m:
        m.setattr("app.services.execution_service.MockAngelOneExecutionAdapter", TestMockAdapter)
        record = exec_service.submit_order(req)
        
        assert record.status == BrokerOrderStatus.PARTIALLY_FILLED
        assert record.executed_quantity == Decimal("6")
        assert record.remaining_quantity == Decimal("4")

def test_timeout_test(exec_service, monkeypatch, test_portfolio, db_session):
    monkeypatch.setattr(settings, "BROKER_PROVIDER", "mock_broker")
    
    acc = PaperAccount(portfolio_id=test_portfolio.id, available_cash=10000.0, initial_cash=10000.0)
    db_session.add(acc)
    db_session.commit()
    
    req = BrokerOrderRequest(
        client_order_id=f"TEST-{uuid.uuid4().hex[:6]}",
        symbol="WIPRO",
        exchange="NSE",
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        order_type="MARKET",
        product="DELIVERY",
        execution_intent=ExecutionIntent.DELIVERY_LONG_TERM,
        portfolio_id=test_portfolio.id
    )
    
    from app.services.brokers.angel_one.mock_execution import MockAngelOneExecutionAdapter
    class TestMockAdapter(MockAngelOneExecutionAdapter):
        def __init__(self):
            super().__init__()
            self.simulation_mode = "TIMEOUT"
            
    with monkeypatch.context() as m:
        m.setattr("app.services.execution_service.MockAngelOneExecutionAdapter", TestMockAdapter)
        record = exec_service.submit_order(req)
        
        assert record.status == BrokerOrderStatus.UNKNOWN

def test_1000_rupees_test(exec_service, monkeypatch, test_portfolio, db_session):
    # As requested by the user:
    # "Use: cash = ₹1,000. BUY candidate: approved amount = ₹600. Expected: maximum requested deployment = ₹600."
    # We will simulate this through the execution validation logic if we implemented price checks.
    # In my execution service, this is done downstream from AI risk limits, but I will check cash logic in PaperBroker integration.
    
    acc = PaperAccount(portfolio_id=test_portfolio.id, available_cash=1000.0, initial_cash=1000.0)
    db_session.add(acc)
    db_session.commit()
    
    # Execution intent enforces cash bounds. 
    # PaperBroker fallback updates cash properly.
    from app.models.risk import RiskApprovalRecord
    r = RiskApprovalRecord(portfolio_id=test_portfolio.id, decision_id=1, symbol="ABC", asset_type="STOCK", original_decision="BUY", execution_intent="DELIVERY_LONG_TERM", requested_quantity=6, approved_quantity=6, requested_amount=600, approved_amount=600, final_status="APPROVED", risk_profile="MODERATE", analysis_score=80, risk_score=50, checks="{}", warnings="{}", rejection_reasons="{}", modifications="{}")
    db_session.add(r)
    db_session.commit()
    
    monkeypatch.setattr(settings, "BROKER_PROVIDER", "paper")
    exec_record = exec_service.execute_approved_decision(r.id)
    
    db_session.refresh(acc)
    assert acc.available_cash == 400.0
    
    r2 = RiskApprovalRecord(portfolio_id=test_portfolio.id, decision_id=2, symbol="XYZ", asset_type="STOCK", original_decision="BUY", execution_intent="DELIVERY_LONG_TERM", requested_quantity=5, approved_quantity=5, requested_amount=500, approved_amount=500, final_status="APPROVED", risk_profile="MODERATE", analysis_score=80, risk_score=50, checks="{}", warnings="{}", rejection_reasons="{}", modifications="{}")
    db_session.add(r2)
    db_session.commit()
    
    # 500 requested, but cash is 400.
    # We mock execute_buy to fail if cash < required_cash
    exec_record2 = exec_service.execute_approved_decision(r2.id)
    assert exec_record2.status.name == "FAILED"
    assert "Insufficient cash" in exec_record2.error_message
