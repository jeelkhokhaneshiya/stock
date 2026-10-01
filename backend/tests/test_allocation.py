import pytest
from decimal import Decimal
from app.schemas.allocation import AllocationPreviewRequest, AllocationCandidate

def get_auth_header(client):
    try:
        client.post("/api/v1/auth/register", json={"email": "alloc@example.com", "password": "pass"})
    except:
        pass
    response = client.post("/api/v1/auth/login", data={"username": "alloc@example.com", "password": "pass"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}

def test_empty_portfolio_allocation(client):
    headers = get_auth_header(client)
    req = {
        "capital": 10000,
        "risk_profile": "MODERATE",
        "investment_horizon": "LONG_TERM",
        "candidates": [
            {"symbol": "TCS", "asset_type": "STOCK"},
            {"symbol": "NIFTYBEES", "asset_type": "ETF"}
        ]
    }
    resp = client.post("/api/v1/portfolio/test_port_1/allocation-preview", json=req, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["available_capital"]) == 10000.0
    assert float(data["cash_reserve"]) > 0
    
    recs = [r for r in data["recommendations"] if r["action"] != "REJECTED"]
    assert len(data["recommendations"]) == 2
    for r in recs:
        assert float(r["allocation_amount"]) > 0
        assert float(r["recommended_quantity"]) > 0

def test_small_capital_500(client):
    headers = get_auth_header(client)
    # 500 capital, TCS costs ~300+ in mock, reserve is 50. Leaves 450. Might buy 1 share.
    req = {
        "capital": 500,
        "risk_profile": "MODERATE",
        "investment_horizon": "LONG_TERM",
        "candidates": [
            {"symbol": "A", "asset_type": "STOCK"} # price = 97.5 (ord(A)=65 * 1.5)
        ]
    }
    resp = client.post("/api/v1/portfolio/test_port_2/allocation-preview", json=req, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["available_capital"]) == 500.0
    total_allocated = sum(float(r["allocation_amount"]) for r in data["recommendations"])
    assert total_allocated + float(data["unallocated_cash"]) == float(data["capital_available_for_allocation"])

def test_decimal_rounding_mutual_fund(client):
    headers = get_auth_header(client)
    req = {
        "capital": 5000,
        "risk_profile": "MODERATE",
        "investment_horizon": "LONG_TERM",
        "candidates": [
            {"symbol": "MF123", "asset_type": "MUTUAL_FUND"}
        ]
    }
    resp = client.post("/api/v1/portfolio/test_port_3/allocation-preview", json=req, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    # Mutual funds should allow fractional quantities
    recs = [r for r in data["recommendations"] if r["symbol"] == "MF123" and r["action"] != "REJECTED"]
    if recs:
        mf = recs[0]
        qty = str(mf["recommended_quantity"])
        assert float(qty) > 0
        
def test_rejected_allocation(client):
    headers = get_auth_header(client)
    req = {
        "capital": 10000,
        "risk_profile": "CONSERVATIVE", # Reject high risk or low suitability
        "investment_horizon": "LONG_TERM",
        "candidates": [
            {"symbol": "INVALID_SYM", "asset_type": "STOCK"} # Will fail analysis
        ]
    }
    resp = client.post("/api/v1/portfolio/test_port_4/allocation-preview", json=req, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    # Warnings should contain the error
    assert any("Failed to analyze" in w for w in data["warnings"])
