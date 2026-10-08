import asyncio
import httpx
import logging
import pytest

logging.basicConfig(level=logging.INFO)

@pytest.mark.asyncio
async def test_concurrency():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Login to get JWT
        res = await client.post("http://localhost:8000/api/v1/auth/login", data={"username": "test@test.com", "password": "password"})
        if res.status_code != 200:
            reg = await client.post("http://localhost:8000/api/v1/auth/register", json={"email": "test@test.com", "password": "password", "name": "Test User"})
            if reg.status_code != 200 and reg.status_code != 201 and reg.status_code != 400: # 400 is already exists
                logging.error(f"Register failed: {reg.text}")
                return
            res = await client.post("http://localhost:8000/api/v1/auth/login", data={"username": "test@test.com", "password": "password"})
        if res.status_code != 200:
            logging.error(f"Login failed: {res.text}")
            return
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Hit multiple endpoints simultaneously
        endpoints = [
            "/api/v1/broker-monitoring/funds",
            "/api/v1/broker-monitoring/holdings",
            "/api/v1/broker-monitoring/positions",
            "/api/v1/broker-monitoring/orders",
            "/api/v1/broker-monitoring/account"
        ]

        async def fetch(url):
            r = await client.get(f"http://localhost:8000{url}", headers=headers)
            logging.info(f"{url}: {r.status_code}")
            return r

        tasks = [fetch(ep) for ep in endpoints]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(test_concurrency())
