import pytest
from app.schemas.decision import DecisionContext
from app.models.enums import AssetType

def get_auth_header(client):
    try:
        client.post("/api/v1/auth/register", json={"email": "ai@example.com", "password": "pass"})
    except:
        pass
    response = client.post("/api/v1/auth/login", data={"username": "ai@example.com", "password": "pass"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}

def make_context():
    return {
        "symbol": "TCS",
        "asset_type": "STOCK",
        "portfolio_id": "test_port",
        "analysis_report": {
            "long_term_suitability_score": 85.0,
            "risk_score": 80.0,
            "analysis_confidence": "HIGH"
        },
        "allocation_recommendation": {
            "allocation_amount": 1000,
            "allocation_percent": 10,
            "recommended_quantity": 2
        },
        "risk_profile": "MODERATE",
        "investment_horizon": "LONG_TERM",
        "available_capital": 10000.0,
        "warnings": []
    }

def test_valid_buy_decision(client):
    headers = get_auth_header(client)
    ctx = make_context()
    resp = client.post("/api/v1/decision/preview?mock_mode=VALID_BUY", json=ctx, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["decision"] == "BUY"
    assert resp.json()["id"] > 0

def test_guardrail_insufficient_confidence(client):
    headers = get_auth_header(client)
    ctx = make_context()
    ctx["analysis_report"]["analysis_confidence"] = "INSUFFICIENT"
    resp = client.post("/api/v1/decision/preview?mock_mode=VALID_BUY", json=ctx, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["decision"] == "AVOID" # Overridden by guardrail

def test_guardrail_very_high_risk(client):
    headers = get_auth_header(client)
    ctx = make_context()
    ctx["analysis_report"]["risk_score"] = 20.0 # High risk
    resp = client.post("/api/v1/decision/preview?mock_mode=VALID_BUY", json=ctx, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["decision"] == "AVOID"

def test_invalid_json(client):
    headers = get_auth_header(client)
    ctx = make_context()
    resp = client.post("/api/v1/decision/preview?mock_mode=INVALID_JSON", json=ctx, headers=headers)
    assert resp.status_code == 400
    assert "Invalid JSON" in resp.json()["detail"]

def test_timeout(client):
    headers = get_auth_header(client)
    ctx = make_context()
    resp = client.post("/api/v1/decision/preview?mock_mode=TIMEOUT", json=ctx, headers=headers)
    assert resp.status_code == 400

def test_hallucinated_data_guardrail(client):
    headers = get_auth_header(client)
    ctx = make_context()
    resp = client.post("/api/v1/decision/preview?mock_mode=HALLUCINATED_DATA", json=ctx, headers=headers)
    assert resp.status_code == 400
    assert "AI_DECISION_FAILED" in resp.json()["detail"]

def test_decision_persistence_and_retrieval(client):
    headers = get_auth_header(client)
    ctx = make_context()
    resp = client.post("/api/v1/decision/preview?mock_mode=VALID_HOLD", json=ctx, headers=headers)
    assert resp.status_code == 200
    d_id = resp.json()["id"]
    
    get_resp = client.get(f"/api/v1/decision/{d_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["decision"] == "HOLD"
    assert get_resp.json()["symbol"] == "TCS"
