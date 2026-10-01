import pytest
from pydantic import ValidationError
from app.schemas.risk import ExecutionRequest, RiskApprovalRequest, ExecutionIntent
from app.schemas.decision import DecisionRecommendation

def get_auth_header(client):
    try:
        client.post("/api/v1/auth/register", json={"email": "risk@example.com", "password": "pass"})
    except:
        pass
    response = client.post("/api/v1/auth/login", data={"username": "risk@example.com", "password": "pass"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}

def make_req(decision_type="BUY", rec_amt=1000, rec_qty=10, asset="STOCK", price=100, cash=5000, curr_qty=0, exposure=0, conf="HIGH"):
    return {
        "decision": {
            "decision": decision_type,
            "confidence": 0.9,
            "risk_level": "MODERATE",
            "recommended_allocation_percent": 10.0,
            "recommended_amount": rec_amt,
            "recommended_quantity": rec_qty,
            "holding_period": "LONG_TERM",
            "reason": "Test",
            "supporting_factors": [],
            "risk_factors": [],
            "reassessment_conditions": []
        },
        "portfolio_id": "test_port",
        "symbol": "TCS",
        "asset_type": asset,
        "current_price": price,
        "available_cash": cash,
        "current_quantity": curr_qty,
        "current_exposure": exposure,
        "portfolio_total_value": 10000,
        "risk_profile": "MODERATE",
        "analysis_confidence": conf,
        "data_freshness_minutes": 0,
        "sector": "IT",
        "sector_exposure": 0
    }

def test_valid_buy_approval(client):
    headers = get_auth_header(client)
    req = make_req()
    resp = client.post("/api/v1/risk/approve", json=req, headers=headers)
    if resp.status_code != 200:
        print(resp.text)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "APPROVED"
    assert data["execution_intent"] == "DELIVERY_LONG_TERM"

def test_valid_sell_approval(client):
    headers = get_auth_header(client)
    req = make_req("SELL", curr_qty=10) # holding 10
    resp = client.post("/api/v1/risk/approve", json=req, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"

def test_sell_without_holding_rejection(client):
    headers = get_auth_header(client)
    req = make_req("SELL", curr_qty=0)
    resp = client.post("/api/v1/risk/approve", json=req, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"

def test_excessive_sell_rejection(client):
    headers = get_auth_header(client)
    req = make_req("SELL", rec_qty=20, curr_qty=10)
    resp = client.post("/api/v1/risk/approve", json=req, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"

def test_hold_avoid_no_execution(client):
    headers = get_auth_header(client)
    for d in ["HOLD", "AVOID"]:
        req = make_req(d)
        resp = client.post("/api/v1/risk/approve", json=req, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "NO_EXECUTION_REQUIRED"

def test_insufficient_cash(client):
    headers = get_auth_header(client)
    req = make_req(rec_amt=5000, cash=1000)
    resp = client.post("/api/v1/risk/approve", json=req, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"

def test_stale_data(client):
    headers = get_auth_header(client)
    req = make_req()
    req["data_freshness_minutes"] = 30
    resp = client.post("/api/v1/risk/approve", json=req, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"

def test_insufficient_confidence(client):
    headers = get_auth_header(client)
    req = make_req(conf="INSUFFICIENT")
    resp = client.post("/api/v1/risk/approve", json=req, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"

def test_concentration_limit_modification(client):
    headers = get_auth_header(client)
    # MODERATE max single stock is typically 15%. Port = 10000. Max = 1500.
    # Current exposure = 1000. Add = 1000. Total = 2000 (exceeds 1500).
    # Should modify amount to 500.
    req = make_req(rec_amt=1000, exposure=1000)
    req["portfolio_total_value"] = 10000
    req["current_price"] = 100
    resp = client.post("/api/v1/risk/approve", json=req, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "MODIFIED"
    assert float(data["approved_amount"]) == 100.0
    assert float(data["approved_quantity"]) == 1.0

def test_intraday_execution_schema_rejection():
    with pytest.raises(ValidationError):
        ExecutionRequest(
            symbol="TCS",
            asset_type="STOCK",
            side="BUY",
            quantity=10,
            execution_intent="INTRADAY", # Invalid
            order_type="MARKET",
            portfolio_id="test"
        )
        
    with pytest.raises(ValidationError):
        ExecutionRequest(
            symbol="TCS",
            asset_type="STOCK",
            side="BUY",
            quantity=10,
            execution_intent="MARGIN", # Invalid
            order_type="MARKET",
            portfolio_id="test"
        )

def test_mutual_fund_fractional(client):
    headers = get_auth_header(client)
    req = make_req(rec_qty=1.5, asset="MUTUAL_FUND")
    resp = client.post("/api/v1/risk/approve", json=req, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"
    assert float(resp.json()["approved_quantity"]) == 1.5

def test_stock_fractional_rejected(client):
    headers = get_auth_header(client)
    req = make_req(rec_qty=1.5, asset="STOCK")
    resp = client.post("/api/v1/risk/approve", json=req, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"

def test_persistence(client):
    headers = get_auth_header(client)
    req = make_req()
    resp = client.post("/api/v1/risk/approve", json=req, headers=headers)
    assert resp.status_code == 200
    a_id = resp.json()["id"]
    
    get_resp = client.get(f"/api/v1/risk/{a_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "APPROVED"
