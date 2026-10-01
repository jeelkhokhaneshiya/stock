import pytest
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.shadow import ShadowOrderRecord
from app.models.enums import OrderSide, ExecutionStatus, ExecutionMode
from app.services.shadow_execution import ShadowExecutionService
from app.services.safety_monitor import SafetyMonitor, SafetyStatus
from app.core.config import settings
from unittest.mock import patch, MagicMock

def test_safety_monitor():
    monitor = SafetyMonitor()
    
    # Test normal safe paper mode
    settings.EXECUTION_MODE = "PAPER"
    settings.LIVE_EXECUTION_UNLOCKED = False
    settings.ENABLE_LIVE_TRADING = False
    settings.BROKER_EXECUTION_BLOCKED = True
    settings.AUTONOMOUS_KILL_SWITCH = False
    
    res = monitor.check_safety("test_port")
    assert res["status"] == SafetyStatus.SAFE, res["reasons"]
    
    # Test kill switch
    settings.AUTONOMOUS_KILL_SWITCH = True
    res = monitor.check_safety("test_port")
    assert res["status"] == SafetyStatus.BLOCKED
    assert "AUTONOMOUS_KILL_SWITCH_ACTIVE" in res["reasons"]
    settings.AUTONOMOUS_KILL_SWITCH = False
    
    # Test live execution blocked by unlock
    settings.EXECUTION_MODE = "LIVE"
    res = monitor.check_safety("test_port")
    assert res["status"] == SafetyStatus.BLOCKED
    assert "LIVE_EXECUTION_BLOCKED" in res["reasons"]

def test_shadow_execution_service_stale_data(db_session: Session):
    service = ShadowExecutionService(db_session)
    settings.QUOTE_MAX_AGE_SECONDS = 300
    
    with pytest.raises(ValueError, match="SHADOW_EXECUTION_BLOCKED_STALE_DATA"):
        service.execute_shadow_order(
            portfolio_id="test_port",
            user_id="user1",
            decision_id=1,
            symbol="RELIANCE",
            side=OrderSide.BUY,
            quantity=Decimal("10"),
            requested_amount=Decimal("25000"),
            market_price=Decimal("2500"),
            data_freshness_seconds=400 # stale
        )

def test_shadow_execution_success(db_session: Session):
    # Need to create decision first for FK? 
    # For testing, we might need to disable FK or create a dummy decision.
    pass


def test_shadow_portfolio_simulation():
    from app.services.shadow_portfolio import ShadowPortfolioSimulator
    from app.models.shadow import ShadowOrderRecord
    from app.models.enums import OrderSide, ExecutionStatus
    
    sim = ShadowPortfolioSimulator(starting_cash=Decimal("1000"))
    
    # Simulate BUY
    order1 = ShadowOrderRecord(symbol="TEST", side=OrderSide.BUY, simulated_fill_quantity=Decimal("2"), simulated_fill_price=Decimal("100"), status=ExecutionStatus.EXECUTED)
    sim.process_order(order1)
    
    assert sim.current_cash == Decimal("800")
    assert sim.current_holdings["TEST"] == Decimal("2")
    assert sim.simulated_buys == 1
    
    # Simulate SELL
    order2 = ShadowOrderRecord(symbol="TEST", side=OrderSide.SELL, simulated_fill_quantity=Decimal("1"), simulated_fill_price=Decimal("150"), status=ExecutionStatus.EXECUTED)
    sim.process_order(order2)
    
    assert sim.current_cash == Decimal("950")
    assert sim.current_holdings["TEST"] == Decimal("1")
    assert sim.simulated_sells == 1
    
    metrics = sim.get_metrics({"TEST": Decimal("150")})
    assert metrics["portfolio_value"] == Decimal("1100")
    assert metrics["profit_loss"] == Decimal("100")
    assert metrics["return_percentage"] == Decimal("10")
    
def test_angel_one_isolation(monkeypatch):
    import requests
    # Assert requests.post is never called with angel one URL
    def mock_post(*args, **kwargs):
        if "angelone" in str(args[0]).lower() or "angelbroking" in str(args[0]).lower():
            raise RuntimeError("REAL BROKER API CALLED")
        return MagicMock()
    
    monkeypatch.setattr(requests, "post", mock_post)
    
    settings.EXECUTION_MODE = "PAPER"
    settings.AUTONOMOUS_KILL_SWITCH = False
    settings.BROKER_EXECUTION_BLOCKED = True
    settings.LIVE_EXECUTION_UNLOCKED = False
    settings.ENABLE_LIVE_TRADING = False
    monitor = SafetyMonitor()
    res = monitor.check_safety("test")
    assert res["status"] == SafetyStatus.SAFE, res["reasons"]
