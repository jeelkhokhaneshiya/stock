import pytest
from app.models.enums import AssetType

def get_auth_header(client):
    client.post("/api/v1/auth/register", json={"email": "paper@example.com", "password": "pass"})
    response = client.post("/api/v1/auth/login", data={"username": "paper@example.com", "password": "pass"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def create_portfolio(client, headers):
    resp = client.post("/api/v1/portfolios", json={"name": "Paper Port"}, headers=headers)
    return resp.json()["id"]

def test_paper_broker_flow(client):
    headers = get_auth_header(client)
    port_id = create_portfolio(client, headers)
    
    # 1. Create paper account, 2. Initial cash is correct
    resp = client.post("/api/v1/paper/accounts", json={"portfolio_id": port_id, "initial_cash": 1000.0}, headers=headers)
    assert resp.status_code == 200
    account_id = resp.json()["id"]
    assert resp.json()["initial_cash"] == 1000.0
    assert resp.json()["available_cash"] == 1000.0

    # 3. Successful BUY, 4. Cash decreases, 5. Holding increases, 6. Average price correct
    req_buy = {
        "client_order_id": "buy1",
        "symbol": "TCS",
        "instrument_type": "STOCK",
        "quantity": 2,
        "price": 100
    }
    resp = client.post(f"/api/v1/paper/accounts/{account_id}/orders/buy", json=req_buy, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "FILLED"
    
    acc_resp = client.get(f"/api/v1/paper/accounts/{account_id}", headers=headers)
    assert acc_resp.json()["available_cash"] == 800.0

    hold_resp = client.get(f"/api/v1/paper/accounts/{account_id}/holdings", headers=headers)
    assert len(hold_resp.json()) == 1
    assert hold_resp.json()[0]["quantity"] == 2.0
    assert hold_resp.json()[0]["average_price"] == 100.0

    # Another buy to check avg price
    req_buy2 = {
        "client_order_id": "buy2",
        "symbol": "TCS",
        "instrument_type": "STOCK",
        "quantity": 2,
        "price": 120
    }
    client.post(f"/api/v1/paper/accounts/{account_id}/orders/buy", json=req_buy2, headers=headers)
    hold_resp = client.get(f"/api/v1/paper/accounts/{account_id}/holdings", headers=headers)
    assert hold_resp.json()[0]["quantity"] == 4.0
    assert hold_resp.json()[0]["average_price"] == 110.0
    
    acc_resp = client.get(f"/api/v1/paper/accounts/{account_id}", headers=headers)
    assert acc_resp.json()["available_cash"] == 560.0

    # 7. Successful SELL, 8. Cash increases, 9. Realized P&L
    req_sell = {
        "client_order_id": "sell1",
        "symbol": "TCS",
        "instrument_type": "STOCK",
        "quantity": 4,
        "price": 150
    }
    resp = client.post(f"/api/v1/paper/accounts/{account_id}/orders/sell", json=req_sell, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "FILLED"
    
    acc_resp = client.get(f"/api/v1/paper/accounts/{account_id}", headers=headers)
    assert acc_resp.json()["available_cash"] == 560.0 + (4 * 150) # 1160.0

    # Holdings should be empty now
    hold_resp = client.get(f"/api/v1/paper/accounts/{account_id}/holdings", headers=headers)
    assert len(hold_resp.json()) == 0

    # 10. Insufficient cash BUY is rejected
    req_buy3 = {
        "client_order_id": "buy3",
        "symbol": "INFY",
        "instrument_type": "STOCK",
        "quantity": 100,
        "price": 1000 # 100,000 > 1160
    }
    resp = client.post(f"/api/v1/paper/accounts/{account_id}/orders/buy", json=req_buy3, headers=headers)
    assert resp.json()["status"] == "REJECTED"
    assert resp.json()["reject_reason"] == "Insufficient cash"

    # 11. Selling more than owned is rejected
    req_sell2 = {
        "client_order_id": "sell2",
        "symbol": "TCS",
        "instrument_type": "STOCK",
        "quantity": 1,
        "price": 150
    }
    resp = client.post(f"/api/v1/paper/accounts/{account_id}/orders/sell", json=req_sell2, headers=headers)
    assert resp.json()["status"] == "REJECTED"
    assert resp.json()["reject_reason"] == "Insufficient holding quantity"

    # 12. Negative quantity rejected
    req_neg_qty = {
        "client_order_id": "neg1",
        "symbol": "TCS",
        "instrument_type": "STOCK",
        "quantity": -5,
        "price": 100
    }
    resp = client.post(f"/api/v1/paper/accounts/{account_id}/orders/buy", json=req_neg_qty, headers=headers)
    assert resp.status_code == 400

    # 13. Negative price rejected
    req_neg_px = {
        "client_order_id": "neg2",
        "symbol": "TCS",
        "instrument_type": "STOCK",
        "quantity": 5,
        "price": -100
    }
    resp = client.post(f"/api/v1/paper/accounts/{account_id}/orders/buy", json=req_neg_px, headers=headers)
    assert resp.status_code == 400

    # 14. Duplicate client_order_id
    req_dup = {
        "client_order_id": "buy1", # already used
        "symbol": "TCS",
        "instrument_type": "STOCK",
        "quantity": 2,
        "price": 100
    }
    resp = client.post(f"/api/v1/paper/accounts/{account_id}/orders/buy", json=req_dup, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == 1 # Returns the existing first order
