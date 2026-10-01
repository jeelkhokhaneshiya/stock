def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Service is healthy", "database": "connected"}

def test_register_user(client):
    response = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "testpassword123"
    })
    assert response.status_code == 201  # 201 Created is correct for registration
    assert response.json()["email"] == "test@example.com"
    assert "id" in response.json()

def test_duplicate_register(client):
    client.post("/api/v1/auth/register", json={"email": "test2@example.com", "password": "pass"})
    response = client.post("/api/v1/auth/register", json={"email": "test2@example.com", "password": "pass"})
    assert response.status_code == 400

def test_login(client):
    client.post("/api/v1/auth/register", json={"email": "test3@example.com", "password": "pass"})
    response = client.post("/api/v1/auth/login", data={"username": "test3@example.com", "password": "pass"})
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_invalid_login(client):
    response = client.post("/api/v1/auth/login", data={"username": "notfound@example.com", "password": "bad"})
    assert response.status_code == 401  # 401 Unauthorized is correct per RFC 6749

def test_create_portfolio(client):
    client.post("/api/v1/auth/register", json={"email": "test4@example.com", "password": "pass"})
    login_response = client.post("/api/v1/auth/login", data={"username": "test4@example.com", "password": "pass"})
    token = login_response.json()["access_token"]
    
    response = client.post("/api/v1/portfolios", json={"name": "My Portfolio"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["name"] == "My Portfolio"
    assert response.json()["base_currency"] == "INR"

def test_get_portfolios(client):
    client.post("/api/v1/auth/register", json={"email": "test5@example.com", "password": "pass"})
    token = client.post("/api/v1/auth/login", data={"username": "test5@example.com", "password": "pass"}).json()["access_token"]
    
    client.post("/api/v1/portfolios", json={"name": "Port 1"}, headers={"Authorization": f"Bearer {token}"})
    response = client.get("/api/v1/portfolios", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert len(response.json()) == 1
