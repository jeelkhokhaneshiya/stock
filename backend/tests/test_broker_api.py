import pytest
from fastapi.testclient import TestClient

def test_get_broker_status_unauthorized(client: TestClient):
    response = client.get("/api/v1/broker/status/1")
    assert response.status_code == 401

def test_get_broker_status_success(client: TestClient, auth_headers, test_portfolio, db_session, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "BROKER_PROVIDER", "paper")
    from app.models.paper import PaperAccount
    account = PaperAccount(portfolio_id=test_portfolio.id, available_cash=5000.0, initial_cash=5000.0)
    db_session.add(account)
    db_session.commit()
    
    response = client.get(f"/api/v1/broker/status/{test_portfolio.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "paper"
    assert data["mode"] == "PAPER"
    assert data["authenticated"] is True

def test_get_broker_portfolio_success(client: TestClient, auth_headers, test_portfolio, db_session, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "BROKER_PROVIDER", "paper")
    from app.models.paper import PaperAccount
    account = PaperAccount(portfolio_id=test_portfolio.id, available_cash=5000.0, initial_cash=5000.0)
    db_session.add(account)
    db_session.commit()
    
    response = client.get(f"/api/v1/broker/portfolio/{test_portfolio.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "cash" in data
    assert data["cash"]["available_cash"] == "5000.0"

def test_broker_ownership_isolation(client: TestClient, auth_headers, db_session):
    # Try accessing portfolio 999 which does not exist or user doesn't own
    response = client.get("/api/v1/broker/status/999", headers=auth_headers)
    assert response.status_code == 404
