import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

from app.models.user import User
from app.models.portfolio import Portfolio

@pytest.fixture
def autonomous_enabled():
    old = settings.AUTONOMOUS_MODE
    settings.AUTONOMOUS_MODE = True
    yield
    settings.AUTONOMOUS_MODE = old

def test_trigger_cycle_unauthorized(client: TestClient, db_session):
    response = client.post("/api/v1/autonomous/cycle/1")
    assert response.status_code == 401

def test_trigger_cycle_disabled(client: TestClient, auth_headers, db_session):
    settings.AUTONOMOUS_MODE = False
    response = client.post("/api/v1/autonomous/cycle/1", headers=auth_headers)
    assert response.status_code == 400
    assert "disabled" in response.json()["detail"]

def test_trigger_cycle_not_found(client: TestClient, auth_headers, autonomous_enabled):
    response = client.post("/api/v1/autonomous/cycle/999", headers=auth_headers)
    assert response.status_code == 404

def test_trigger_cycle_success(client: TestClient, auth_headers, autonomous_enabled, test_portfolio, db_session):
    from app.models.paper import PaperAccount
    account = PaperAccount(portfolio_id=test_portfolio.id, available_cash=1000.0, initial_cash=1000.0)
    db_session.add(account)
    db_session.commit()
    
    response = client.post(f"/api/v1/autonomous/cycle/{test_portfolio.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "cycle_id" in data
    assert data["status"] in ["RUNNING", "COMPLETED", "PARTIAL", "FAILED"]
    assert data["portfolio_id"] == str(test_portfolio.id)

def test_get_cycle_not_found(client: TestClient, auth_headers):
    response = client.get("/api/v1/autonomous/cycle/999", headers=auth_headers)
    assert response.status_code == 404

def test_get_status_success(client: TestClient, auth_headers, test_portfolio, db_session):
    from app.models.paper import PaperAccount
    account = db_session.query(PaperAccount).filter(PaperAccount.portfolio_id == test_portfolio.id).first()
    if not account:
        account = PaperAccount(portfolio_id=test_portfolio.id, available_cash=1000.0, initial_cash=1000.0)
        db_session.add(account)
        db_session.commit()
    
    response = client.get(f"/api/v1/autonomous/status/{test_portfolio.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["broker_mode"] == "PAPER"
    assert data["autonomous_mode"] == settings.AUTONOMOUS_MODE
    assert "current_cash" in data

def test_get_cycle_executions(client: TestClient, auth_headers):
    response = client.get("/api/v1/autonomous/cycle/999/executions", headers=auth_headers)
    assert response.status_code == 404

def test_live_broker_not_exposed():
    # Sanity check: Ensure ENABLE_LIVE_TRADING is false
    assert settings.ENABLE_LIVE_TRADING is False
    assert settings.TRADING_MODE == "paper"
