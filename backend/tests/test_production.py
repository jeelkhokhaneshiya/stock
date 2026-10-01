import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

def test_cors_allowed_origin(client: TestClient):
    origin = settings.FRONTEND_ORIGIN.split(",")[0] if settings.FRONTEND_ORIGIN else "http://localhost:5173"
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET"
        }
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin

def test_cors_disallowed_origin(client: TestClient):
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://malicious-site.com",
            "Access-Control-Request-Method": "GET"
        }
    )
    # The middleware will just not attach the allow-origin header
    assert "access-control-allow-origin" not in response.headers

def test_security_headers(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

def test_readiness_endpoint_success(client: TestClient):
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert "safety_checks" in response.json()
    # Ensure no secrets leak
    assert "password" not in str(response.json()).lower()
    assert "secret" not in str(response.json()).lower()
    assert "api_key" not in str(response.json()).lower()

def test_readiness_endpoint_safety_failure(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LIVE_TRADING", True)
    response = client.get("/api/v1/ready")
    assert response.status_code == 503
    assert response.json()["detail"] == "Not ready: Safety flags invalid. Live trading is currently unsupported and must be explicitly disabled."

def test_safety_flags_enforced():
    assert settings.ENABLE_LIVE_TRADING is False
    assert settings.LIVE_EXECUTION_UNLOCKED is False
    assert settings.BROKER_EXECUTION_BLOCKED is True
