import pytest
from app.schemas.analysis import AnalysisReport

def get_auth_header(client):
    try:
        client.post("/api/v1/auth/register", json={"email": "analysis@example.com", "password": "pass"})
    except:
        pass
    response = client.post("/api/v1/auth/login", data={"username": "analysis@example.com", "password": "pass"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}

def test_analyze_stock(client):
    headers = get_auth_header(client)
    resp = client.get("/api/v1/analysis/stock/TCS", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "TCS"
    assert data["asset_type"] == "STOCK"
    assert "long_term_suitability_score" in data
    assert data["analysis_confidence"] in ["HIGH", "MEDIUM", "LOW", "INSUFFICIENT"]
    assert data["fundamental_score"] is not None

def test_analyze_etf(client):
    headers = get_auth_header(client)
    resp = client.get("/api/v1/analysis/etf/NIFTYBEES", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "NIFTYBEES"
    assert data["asset_type"] == "ETF"
    assert data["fundamental_score"] is not None  # ETFs don't use stock fundamentals
    assert data["technical_score"] is not None

def test_analyze_mutual_fund(client):
    headers = get_auth_header(client)
    resp = client.get("/api/v1/analysis/mutual-fund/MF123", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["asset_type"] == "MUTUAL_FUND"

def test_analyze_generic_endpoint(client):
    headers = get_auth_header(client)
    resp = client.get("/api/v1/analysis/STOCK/RELIANCE", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["symbol"] == "RELIANCE"

def test_analyze_invalid_symbol(client):
    headers = get_auth_header(client)
    resp = client.get("/api/v1/analysis/stock/INVALID_SYM", headers=headers)
    assert resp.status_code == 400

def test_explanation_generation(client):
    headers = get_auth_header(client)
    resp = client.get("/api/v1/analysis/stock/TCS", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "score of" in data["explanation"]
    assert type(data["strengths"]) == list
