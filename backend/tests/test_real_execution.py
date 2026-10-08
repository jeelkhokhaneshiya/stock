import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import uuid

from app.core.config import settings
from app.schemas.execution import OrderIntent, OrderState
from app.services.execution.real_execution import RealExecutionEngine, ExecutionError

class DummyRealClient:
    def __init__(self):
        self.is_mock = False
        
    def place_order(self, *args, **kwargs):
        return {"status": True, "data": {"orderid": "12345"}}
        
    def get_ltp(self, *args, **kwargs):
        return 100.0
        
    def get_order_book(self, *args, **kwargs):
        return {"data": [{"orderid": "12345", "status": "COMPLETE"}]}

@pytest.fixture
def mock_client():
    return DummyRealClient()

@pytest.fixture
def mock_pm():
    pm = MagicMock()
    pm.get_funds.return_value = {"available_cash": 10000.0}
    pm.get_holdings.return_value = {"holdings": [{"symbol": "TCS", "quantity": 10}]}
    return pm

@pytest.fixture
def execution_engine(mock_client, mock_pm, tmp_path):
    audit_file = tmp_path / "audit.jsonl"
    return RealExecutionEngine(mock_client, mock_pm, str(audit_file))

@pytest.fixture(autouse=True)
def setup_env():
    settings.EXECUTION_MODE = "CONFIRMATION_REQUIRED"
    settings.AUTONOMOUS_KILL_SWITCH = False
    settings.MIN_CASH_RESERVE = 100.0
    yield

def create_intent(tx_type="BUY", qty=10, product="DELIVERY", price=0.0, est=1000.0, symbol="INFY"):
    return OrderIntent(
        intent_id=str(uuid.uuid4()),
        symbol=symbol,
        symboltoken="1111",
        exchange="NSE",
        transaction_type=tx_type,
        product_type=product,
        order_type="MARKET",
        quantity=qty,
        price=price,
        estimated_value=est,
        decision_reason="Test",
        timestamp=datetime.now(timezone.utc)
    )

def test_01_buy_confirmation(execution_engine):
    intent = create_intent("BUY", 10, est=1000.0)
    preview = execution_engine.create_order_preview(intent, {"ltp": 100.0})
    conf = execution_engine.confirm_order(preview.preview_id, "user1")
    res = execution_engine.execute_confirmed_order(conf.confirmation_id, intent)
    assert res.status == OrderState.EXECUTED
    assert res.broker_order_id == "12345"

def test_02_sell_confirmation(execution_engine):
    intent = create_intent("SELL", 5, symbol="TCS", est=500.0)
    preview = execution_engine.create_order_preview(intent, {"ltp": 100.0})
    conf = execution_engine.confirm_order(preview.preview_id, "user1")
    res = execution_engine.execute_confirmed_order(conf.confirmation_id, intent)
    assert res.status == OrderState.EXECUTED

def test_03_confirmation_missing(execution_engine):
    intent = create_intent()
    # Execute without confirming
    res = execution_engine.execute_confirmed_order("invalid_conf", intent)
    assert res.status == OrderState.FAILED
    assert "Invalid confirmation" in res.message

def test_04_expired_confirmation(execution_engine):
    intent = create_intent()
    preview = execution_engine.create_order_preview(intent, {"ltp": 100.0})
    conf = execution_engine.confirm_order(preview.preview_id, "user1")
    # simulate expiry
    preview.order_validity_expiry = datetime.now(timezone.utc) - timedelta(seconds=10)
    res = execution_engine.execute_confirmed_order(conf.confirmation_id, intent)
    assert res.status == OrderState.EXECUTION_BLOCKED
    assert "expired" in res.message.lower()

def test_05_changed_price_after_confirmation(execution_engine):
    intent = create_intent()
    preview = execution_engine.create_order_preview(intent, {"ltp": 100.0})
    conf = execution_engine.confirm_order(preview.preview_id, "user1")
    # broker LTP shoots up by 5%
    def fake_get_ltp(*args, **kwargs):
        return 105.0
    execution_engine.client.get_ltp = fake_get_ltp
    res = execution_engine.execute_confirmed_order(conf.confirmation_id, intent)
    assert res.status == OrderState.EXECUTION_BLOCKED
    assert "Price changed materially" in res.message

def test_06_changed_cash_after_confirmation(execution_engine, mock_pm):
    intent = create_intent()
    preview = execution_engine.create_order_preview(intent, {"ltp": 100.0})
    conf = execution_engine.confirm_order(preview.preview_id, "user1")
    # Cash disappears
    mock_pm.get_funds.return_value = {"available_cash": 10.0}
    res = execution_engine.execute_confirmed_order(conf.confirmation_id, intent)
    assert res.status == OrderState.EXECUTION_BLOCKED
    assert "Insufficient cash" in res.message

def test_07_changed_holdings_after_confirmation(execution_engine, mock_pm):
    intent = create_intent("SELL", symbol="TCS")
    preview = execution_engine.create_order_preview(intent, {"ltp": 100.0})
    conf = execution_engine.confirm_order(preview.preview_id, "user1")
    # Holdings disappear
    mock_pm.get_holdings.return_value = {"holdings": []}
    res = execution_engine.execute_confirmed_order(conf.confirmation_id, intent)
    assert res.status == OrderState.EXECUTION_BLOCKED
    assert "Insufficient holdings" in res.message

def test_09_insufficient_cash(execution_engine):
    intent = create_intent("BUY", est=1000000.0)
    preview = execution_engine.create_order_preview(intent, {"ltp": 100000.0})
    conf = execution_engine.confirm_order(preview.preview_id, "user1")
    res = execution_engine.execute_confirmed_order(conf.confirmation_id, intent)
    assert res.status == OrderState.EXECUTION_BLOCKED
    assert "Insufficient cash" in res.message

def test_13_duplicate_order(execution_engine):
    intent = create_intent()
    preview = execution_engine.create_order_preview(intent, {"ltp": 100.0})
    conf = execution_engine.confirm_order(preview.preview_id, "user1")
    res1 = execution_engine.execute_confirmed_order(conf.confirmation_id, intent)
    assert res1.status == OrderState.EXECUTED
    
    # Try duplicate
    intent2 = create_intent()
    preview2 = execution_engine.create_order_preview(intent2, {"ltp": 100.0})
    conf2 = execution_engine.confirm_order(preview2.preview_id, "user2")
    res2 = execution_engine.execute_confirmed_order(conf2.confirmation_id, intent2)
    assert res2.status == OrderState.EXECUTION_BLOCKED
    assert "Duplicate order" in res2.message

def test_14_kill_switch(execution_engine):
    intent = create_intent()
    preview = execution_engine.create_order_preview(intent, {"ltp": 100.0})
    conf = execution_engine.confirm_order(preview.preview_id, "user1")
    settings.AUTONOMOUS_KILL_SWITCH = True
    res = execution_engine.execute_confirmed_order(conf.confirmation_id, intent)
    assert res.status == OrderState.EXECUTION_BLOCKED
    assert "KILL SWITCH ACTIVE" in res.message

def test_17_angel_one_rejection(execution_engine):
    def fake_place_order(*args, **kwargs):
        return {"status": False, "message": "Margin shortfall"}
    execution_engine.client.place_order = fake_place_order
    intent = create_intent()
    preview = execution_engine.create_order_preview(intent, {"ltp": 100.0})
    conf = execution_engine.confirm_order(preview.preview_id, "user1")
    res = execution_engine.execute_confirmed_order(conf.confirmation_id, intent)
    assert res.status == OrderState.FAILED
    assert "Margin shortfall" in res.message

def test_19_reconciliation_mismatch(execution_engine):
    intent = create_intent()
    preview = execution_engine.create_order_preview(intent, {"ltp": 100.0})
    conf = execution_engine.confirm_order(preview.preview_id, "user1")
    res = execution_engine.execute_confirmed_order(conf.confirmation_id, intent)
    
    # Recon mismatch: broker doesn't have the order
    def fake_get_order_book(*args, **kwargs):
        return {"data": []}
    execution_engine.client.get_order_book = fake_get_order_book
    state = execution_engine.reconcile_order(res.broker_order_id)
    assert state == OrderState.RECONCILIATION_REQUIRED

def test_20_unauthorized_confirmation(execution_engine):
    intent = create_intent()
    preview = execution_engine.create_order_preview(intent, {"ltp": 100.0})
    conf = execution_engine.confirm_order(preview.preview_id, "") # Empty user_id
    res = execution_engine.execute_confirmed_order(conf.confirmation_id, intent)
    assert res.status == OrderState.EXECUTION_BLOCKED
    assert "Unauthorized" in res.message

def test_22_mock_provider_blocked(execution_engine):
    execution_engine.client.is_mock = True
    intent = create_intent()
    preview = execution_engine.create_order_preview(intent, {"ltp": 100.0})
    conf = execution_engine.confirm_order(preview.preview_id, "user1")
    res = execution_engine.execute_confirmed_order(conf.confirmation_id, intent)
    assert res.status == OrderState.FAILED
    assert "Mock client detected" in res.message

def test_23_non_delivery_product(execution_engine):
    intent = create_intent(product="INTRADAY")
    with pytest.raises(ExecutionError, match="DELIVERY"):
        execution_engine.create_order_preview(intent, {"ltp": 100.0})
