import pytest
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from app.services.execution.readiness import ExecutionReadinessLayer, ExecutionReadinessError
from app.core.config import settings

@pytest.fixture
def mock_portfolio_manager():
    manager = MagicMock()
    # Setup mock holdings and funds
    manager.get_funds.return_value = {"available_cash": 10000.0}
    manager.get_holdings.return_value = {
        "holdings": [
            {"symbol": "TCS", "quantity": 10, "average_price": 3000.0}
        ]
    }
    manager.client.get_token_for_symbol.return_value = "11536"
    return manager

@pytest.fixture
def readiness_layer(mock_portfolio_manager, tmp_path):
    audit_path = tmp_path / "order_intent_audit.jsonl"
    return ExecutionReadinessLayer(mock_portfolio_manager, audit_log_path=str(audit_path))

@pytest.fixture(autouse=True)
def safe_env():
    # Make sure env is safe
    old_kill = settings.AUTONOMOUS_KILL_SWITCH
    old_live = settings.ENABLE_LIVE_TRADING
    old_blocked = settings.BROKER_EXECUTION_BLOCKED
    old_unlocked = settings.LIVE_EXECUTION_UNLOCKED
    
    settings.AUTONOMOUS_KILL_SWITCH = False
    settings.ENABLE_LIVE_TRADING = False
    settings.BROKER_EXECUTION_BLOCKED = True
    settings.LIVE_EXECUTION_UNLOCKED = False
    
    yield
    
    settings.AUTONOMOUS_KILL_SWITCH = old_kill
    settings.ENABLE_LIVE_TRADING = old_live
    settings.BROKER_EXECUTION_BLOCKED = old_blocked
    settings.LIVE_EXECUTION_UNLOCKED = old_unlocked

def create_decision(action: str, symbol: str, qty: int, est_val: float, age_seconds: int = 0):
    return {
        "symbol": symbol,
        "decision": action,
        "quantity": qty,
        "ltp": 100.0,
        "estimated_investment": est_val,
        "confidence": 0.8,
        "reason": "Test",
        "risks": [],
        "data_source": "mock",
        "timestamp": datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
    }

def test_successful_buy_intent(readiness_layer):
    decision = create_decision("BUY", "INFY", 10, 1000.0)
    intent = readiness_layer.generate_intent(decision)
    
    assert intent.symbol == "INFY"
    assert intent.transaction_type == "BUY"
    assert intent.quantity == 10
    assert intent.estimated_value == 1000.0
    
    # Audit log should exist
    assert os.path.exists(readiness_layer.audit_log_path)
    with open(readiness_layer.audit_log_path, "r") as f:
        lines = f.readlines()
        assert len(lines) == 1
        assert '"transaction_type": "BUY"' in lines[0]

def test_successful_sell_intent(readiness_layer):
    decision = create_decision("SELL", "TCS", 5, 15000.0)
    intent = readiness_layer.generate_intent(decision)
    
    assert intent.symbol == "TCS"
    assert intent.transaction_type == "SELL"
    assert intent.quantity == 5
    
def test_kill_switch_blocks_execution(readiness_layer):
    settings.AUTONOMOUS_KILL_SWITCH = True
    decision = create_decision("BUY", "INFY", 10, 1000.0)
    with pytest.raises(ExecutionReadinessError, match="Kill switch is active"):
        readiness_layer.generate_intent(decision)

def test_live_trading_violation_blocks_execution(readiness_layer):
    old_mode = settings.EXECUTION_MODE
    settings.EXECUTION_MODE = "PAPER" # Should block
    decision = create_decision("BUY", "INFY", 10, 1000.0)
    with pytest.raises(ExecutionReadinessError, match="Safety configuration violated"):
        readiness_layer.generate_intent(decision)
    settings.EXECUTION_MODE = old_mode
def test_decision_freshness_check(readiness_layer):
    decision = create_decision("BUY", "INFY", 10, 1000.0, age_seconds=4000) # Older than 3600
    with pytest.raises(ExecutionReadinessError, match="Decision is too old"):
        readiness_layer.generate_intent(decision)

def test_insufficient_funds_blocks_buy(readiness_layer):
    decision = create_decision("BUY", "INFY", 1000, 15000.0) # We only have 10000
    with pytest.raises(ExecutionReadinessError, match="Insufficient funds"):
        readiness_layer.generate_intent(decision)

def test_insufficient_holdings_blocks_sell(readiness_layer):
    # We only have 10 TCS
    decision = create_decision("SELL", "TCS", 15, 45000.0)
    with pytest.raises(ExecutionReadinessError, match="Insufficient holdings"):
        readiness_layer.generate_intent(decision)

def test_no_holdings_blocks_sell(readiness_layer):
    decision = create_decision("SELL", "INFY", 5, 500.0)
    with pytest.raises(ExecutionReadinessError, match="no holdings found"):
        readiness_layer.generate_intent(decision)

def test_duplicate_order_protection(readiness_layer):
    decision = create_decision("BUY", "INFY", 10, 1000.0)
    # First one succeeds
    readiness_layer.generate_intent(decision)
    # Second identical one fails
    with pytest.raises(ExecutionReadinessError, match="Duplicate order protection"):
        readiness_layer.generate_intent(decision)

def test_rate_limit_protection(readiness_layer):
    # Two different symbols, so no duplicate order error, but rate limit triggers
    decision1 = create_decision("BUY", "INFY", 10, 1000.0)
    decision2 = create_decision("BUY", "HDFC", 10, 1000.0)
    
    readiness_layer.generate_intent(decision1)
    
    with pytest.raises(ExecutionReadinessError, match="Rate limit exceeded"):
        readiness_layer.generate_intent(decision2)

def test_invalid_decision_type(readiness_layer):
    decision = create_decision("WATCH", "INFY", 10, 1000.0)
    with pytest.raises(ExecutionReadinessError, match="does not result in an order intent"):
        readiness_layer.generate_intent(decision)

def test_invalid_quantity(readiness_layer):
    decision = create_decision("BUY", "INFY", -5, 1000.0)
    with pytest.raises(ExecutionReadinessError, match="Invalid quantity"):
        readiness_layer.generate_intent(decision)
