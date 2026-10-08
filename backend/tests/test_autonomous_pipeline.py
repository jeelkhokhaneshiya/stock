import pytest
import os
import json
from unittest.mock import patch, MagicMock

from worker import run_worker, AUDIT_LOG_FILE

@pytest.fixture
def mock_portfolio_manager():
    with patch("worker.PortfolioManager") as mock_pm:
        instance = mock_pm.return_value
        instance.get_full_portfolio_analysis.return_value = {
            "status": "OK",
            "daily_investment_action_plan": [
                {
                    "symbol": "TCS-EQ",
                    "action": "BUY",
                    "quantity": 10,
                    "current_price": 4000.0,
                    "estimated_value": 40000.0,
                    "confidence": 0.8,
                    "reasons": ["Strong thesis"],
                    "risks": []
                }
            ]
        }
        yield instance

@pytest.fixture
def mock_angel_one_client():
    with patch("worker.AngelOneClient") as mock_client_class:
        instance = mock_client_class.return_value
        instance.authenticate = MagicMock()
        yield instance

@pytest.fixture(autouse=True)
def restore_global_state():
    import app.api.deps
    from app.core.config import settings
    old_client = app.api.deps._global_angel_one_client
    old_provider = settings.MARKET_DATA_PROVIDER
    yield
    app.api.deps._global_angel_one_client = old_client
    settings.MARKET_DATA_PROVIDER = old_provider

def test_worker_single_cycle_success(mock_angel_one_client, mock_portfolio_manager, tmp_path):
    # Setup temp file for audit log
    temp_log = tmp_path / "decisions_audit.jsonl"
    
    with patch("worker.AUDIT_LOG_FILE", str(temp_log)):
        with patch.dict(os.environ, {
            "ANGEL_ONE_CLIENT_ID": "test",
            "ANGEL_ONE_PASSWORD": "test",
            "ANGEL_ONE_API_KEY": "test",
            "ANGEL_ONE_TOTP_SECRET": "test"
        }):
            run_worker(once=True)
            
    assert temp_log.exists()
    content = temp_log.read_text().strip()
    assert content
    record = json.loads(content)
    
    assert record["symbol"] == "TCS-EQ"
    assert record["decision"] == "BUY"
    assert record["quantity"] == 10
    assert record["current_price"] == 4000.0
    assert record["estimated_value"] == 40000.0
    assert record["data_source"] == "ANGEL_ONE"

def test_worker_survives_network_failure(mock_angel_one_client, mock_portfolio_manager, tmp_path, caplog):
    temp_log = tmp_path / "decisions_audit.jsonl"
    
    # Force the manager to throw an exception to simulate a network error
    mock_portfolio_manager.get_full_portfolio_analysis.side_effect = Exception("Connection Timeout")
    
    with patch("worker.AUDIT_LOG_FILE", str(temp_log)):
        with patch.dict(os.environ, {
            "ANGEL_ONE_CLIENT_ID": "test",
            "ANGEL_ONE_PASSWORD": "test",
            "ANGEL_ONE_API_KEY": "test",
            "ANGEL_ONE_TOTP_SECRET": "test"
        }):
            run_worker(once=True)
            
    # The script should not exit with error, it should log and survive
    assert "Cycle error: Connection Timeout" in caplog.text
    assert "Worker will survive and retry next cycle" in caplog.text
