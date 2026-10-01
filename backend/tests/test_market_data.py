import pytest
import time
from datetime import datetime, timezone
from app.schemas.market_data import MarketQuote
from app.services.market_data.cache import cache

def get_auth_header(client):
    try:
        client.post("/api/v1/auth/register", json={"email": "market@example.com", "password": "pass"})
    except:
        pass
    response = client.post("/api/v1/auth/login", data={"username": "market@example.com", "password": "pass"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_mock_quote(client):
    headers = get_auth_header(client)
    resp = client.get("/api/v1/market/quote/RELIANCE", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "RELIANCE"
    assert data["price"] > 0
    assert data["data_source"] == "mock"
    assert "timestamp" in data

def test_mock_historical_data(client):
    headers = get_auth_header(client)
    resp = client.get("/api/v1/market/history/RELIANCE?days=5", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["bars"]) > 0
    assert data["bars"][0]["close"] > 0
    assert "timestamp" in data["bars"][0]

def test_mock_company_info(client):
    headers = get_auth_header(client)
    resp = client.get("/api/v1/market/company/RELIANCE", headers=headers)
    assert resp.status_code == 200
    assert "RELIANCE" in resp.json()["name"]

def test_mock_fundamentals(client):
    headers = get_auth_header(client)
    resp = client.get("/api/v1/market/fundamentals/RELIANCE", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["revenue"] > 0

def test_etf_info(client):
    headers = get_auth_header(client)
    resp = client.get("/api/v1/market/etf/NIFTYBEES", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["symbol"] == "NIFTYBEES"

def test_mutual_fund_info(client):
    headers = get_auth_header(client)
    resp = client.get("/api/v1/market/mutual-fund/MF123", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["identifier"] == "MF123"

def test_invalid_symbol_rejection(client):
    headers = get_auth_header(client)
    resp = client.get("/api/v1/market/quote/INVALID_SYM", headers=headers)
    assert resp.status_code == 400

def test_caching_behavior(client):
    headers = get_auth_header(client)
    cache.clear()
    
    # First call
    client.get("/api/v1/market/quote/TCS", headers=headers)
    
    # Check if it's in cache
    cached = cache.get("quote:NSE:TCS", 300)
    assert cached is not None
    assert cached.symbol == "TCS"
