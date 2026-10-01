import pytest
from fastapi.testclient import TestClient
from app.models.paper import PaperAccount

def test_run_reconciliation_api_unauthorized(client: TestClient):
    response = client.post("/api/v1/reconciliation/1/run")
    assert response.status_code == 401

def test_run_reconciliation_api_success(client: TestClient, auth_headers, test_portfolio, db_session, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "BROKER_PROVIDER", "paper")
    acc = PaperAccount(portfolio_id=test_portfolio.id, available_cash=1000.0, initial_cash=1000.0)
    db_session.add(acc)
    db_session.commit()
    
    response = client.post(f"/api/v1/reconciliation/{test_portfolio.id}/run", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "MATCHED"

def test_get_reconciliation_history(client: TestClient, auth_headers, test_portfolio, db_session, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "BROKER_PROVIDER", "paper")
    acc = PaperAccount(portfolio_id=test_portfolio.id, available_cash=1000.0, initial_cash=1000.0)
    db_session.add(acc)
    db_session.commit()
    
    # Run once to generate history
    client.post(f"/api/v1/reconciliation/{test_portfolio.id}/run", headers=auth_headers)
    
    response = client.get(f"/api/v1/reconciliation/{test_portfolio.id}/history", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_reconciliation_ownership_isolation(client: TestClient, auth_headers, db_session):
    # Try accessing portfolio 999 which does not exist or user doesn't own
    response = client.post("/api/v1/reconciliation/999/run", headers=auth_headers)
    assert response.status_code == 404
