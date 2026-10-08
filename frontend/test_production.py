import urllib.request
import urllib.error

base_url = "https://stock-backend-yngm.onrender.com/api/v1"

endpoints = [
    "/broker-monitoring/account",
    "/broker-monitoring/positions",
    "/broker-monitoring/holdings",
    "/broker-monitoring/funds",
    "/broker-monitoring/orders",
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
