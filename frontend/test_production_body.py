import urllib.request
import urllib.error

url = "https://stock-backend-yngm.onrender.com/api/v1/health"
req = urllib.request.Request(url)
try:
    response = urllib.request.urlopen(req)
    print(response.read().decode())
except urllib.error.HTTPError as e:
    print(f"Error {e.code}: {e.read().decode()}")
