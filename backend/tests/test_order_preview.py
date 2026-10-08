from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_order_preview_endpoint():
    payload = {
        "symbol": "RELIANCE-EQ",
        "side": "BUY",
        "quantity": 10,
        "estimated_price": 2500.50,
        "decision": "ACCUMULATE",
        "thesis_status": "THESIS_STRONG",
        "risk_score": 85.0,
        "current_allocation_pct": 5.0,
        "resulting_allocation_pct": 7.5,
        "reasons": ["Good valuation", "Strong trend"],
        "warnings": []
    }
    
    response = client.post("/api/v1/orders/preview", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PREVIEW_READY"
    assert data["symbol"] == "RELIANCE-EQ"
    assert data["estimated_amount"] == 25005.0
    assert "PREVIEW" in data["notice"]
    assert "Explicit human confirmation" in data["notice"]
