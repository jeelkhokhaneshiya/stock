import pytest
import os
import json
from unittest.mock import MagicMock, patch

from app.worker.monitoring_worker import MonitoringWorker, STATE_FILE
from app.services.notification_service import MockNotificationService

@pytest.fixture
def clean_state():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    yield
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)

@pytest.fixture
def mock_worker(clean_state):
    worker = MonitoringWorker(interval_seconds=60)
    worker.notification_service = MockNotificationService()
    worker.client = MagicMock()
    worker.client.auth.is_authenticated.return_value = True
    worker.pm = MagicMock()
    return worker

def test_buy_notification(mock_worker):
    action_plan = [
        {"symbol": "TCS", "action": "BUY", "current_price": 3000, "quantity": 5, "reasons": ["Good thesis"]}
    ]
    mock_worker.pm.get_full_portfolio_analysis.return_value = {
        "status": "OK",
        "daily_investment_action_plan": action_plan
    }
    
    mock_worker.run_cycle()
    
    assert len(mock_worker.notification_service.messages) == 1
    assert "INVESTMENT ALERT: TCS" in mock_worker.notification_service.messages[0]
    assert "*Action:* BUY" in mock_worker.notification_service.messages[0]
    
    # State saved
    assert mock_worker.state["TCS"]["action"] == "BUY"

def test_unchanged_decision_no_notification(mock_worker):
    # Initial state
    mock_worker.state = {
        "INFY": {"action": "SELL", "quantity": 10, "price": 1500}
    }
    
    action_plan = [
        {"symbol": "INFY", "action": "SELL", "current_price": 1495, "quantity": 10, "reasons": ["Broken thesis"]}
    ]
    mock_worker.pm.get_full_portfolio_analysis.return_value = {
        "status": "OK",
        "daily_investment_action_plan": action_plan
    }
    
    mock_worker.run_cycle()
    
    # No new notification since it hasn't changed meaningfully
    assert len(mock_worker.notification_service.messages) == 0

def test_sell_notification(mock_worker):
    action_plan = [
        {"symbol": "INFY", "action": "SELL", "current_price": 1500, "quantity": 10, "reasons": ["Broken thesis"]}
    ]
    mock_worker.pm.get_full_portfolio_analysis.return_value = {
        "status": "OK",
        "daily_investment_action_plan": action_plan
    }
    mock_worker.run_cycle()
    assert len(mock_worker.notification_service.messages) == 1
    assert "*Action:* SELL" in mock_worker.notification_service.messages[0]

def test_invalidation_notification(mock_worker):
    mock_worker.state = {
        "WIPRO": {"action": "BUY", "quantity": 100, "price": 400}
    }
    # Becomes WATCH because of stale data or broken thesis
    action_plan = [
        {"symbol": "WIPRO", "action": "WATCH", "current_price": 400, "reasons": ["Stale data"]}
    ]
    mock_worker.pm.get_full_portfolio_analysis.return_value = {
        "status": "OK",
        "daily_investment_action_plan": action_plan
    }
    mock_worker.run_cycle()
    assert len(mock_worker.notification_service.messages) == 1
    assert "*Action:* WATCH" in mock_worker.notification_service.messages[0]

def test_authentication_failure(mock_worker):
    mock_worker.client.auth.is_authenticated.return_value = False
    with patch.object(mock_worker, '_authenticate', return_value=False) as mock_auth:
        mock_worker.run_cycle()
        mock_auth.assert_called_once()
        # Since _authenticate is mocked to return False (and it usually handles its own notification), 
        # run_cycle just returns.
        assert len(mock_worker.notification_service.messages) == 0

def test_notification_failure_does_not_save_state(mock_worker):
    mock_worker.notification_service.send_notification = MagicMock(return_value=False)
    action_plan = [
        {"symbol": "HDFC", "action": "BUY", "current_price": 1500, "quantity": 10}
    ]
    mock_worker.pm.get_full_portfolio_analysis.return_value = {
        "status": "OK",
        "daily_investment_action_plan": action_plan
    }
    mock_worker.run_cycle()
    assert "HDFC" not in mock_worker.state # State not saved because notification failed

def test_worker_cannot_bypass_confirmation():
    # Verify that the worker code has absolutely no reference to OrderIntent, create_order_preview, or execute_confirmed_order
    with open("app/worker/monitoring_worker.py", "r", encoding="utf-8") as f:
        content = f.read()
    assert "OrderIntent" not in content
    assert "execute_confirmed_order" not in content
    assert "confirm_order" not in content
    # Ensures the boundary is respected
