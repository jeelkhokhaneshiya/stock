import urllib.request
import urllib.error

base_url = "https://stock-backend-yngm.onrender.com"

endpoints = [
    "/health",
    "/api/v1/health",
    "/api/v1/openapi.json",
]

for ep in endpoints:
    url = f"{base_url}{ep}"
    req = urllib.request.Request(url)
    try:
        response = urllib.request.urlopen(req)
        print(f"{ep} -> {response.getcode()}")
    except urllib.error.HTTPError as e:
        print(f"{ep} -> {e.code}")
    except urllib.error.URLError as e:
        print(f"{ep} -> Error: {e.reason}")
