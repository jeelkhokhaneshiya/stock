from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.api import deps

def test_health_check_success(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "connected"

def test_root_health_check_success(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_health_check_db_failure(client: TestClient):
    def override_get_db():
        class MockSession:
            def execute(self, query):
                raise Exception("DB connection lost")
        yield MockSession()

    app.dependency_overrides[deps.get_db] = override_get_db
    try:
        response = client.get("/api/v1/health")
        assert response.status_code == 503
        assert response.json()["detail"] == "Database unavailable"
    finally:
        app.dependency_overrides.clear()
