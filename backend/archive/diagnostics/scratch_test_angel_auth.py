import os
import sys

# Add the backend directory to sys.path
sys.path.append(r"d:\Jeel project\stock\backend")

from app.services.brokers.angel_one.auth import AngelOneAuth
from app.services.brokers.angel_one.client import AngelOneClient

api_key = "HG9nKv2z"
client_id = "AAAG377380"
password = "1611"
totp_secret = "2Z2PJLPPPJJDPX2O3BKFFFHRUU"

try:
    auth = AngelOneAuth(
        api_key=api_key,
        client_id=client_id,
        password=password,
        totp_secret=totp_secret,
    )
    client = AngelOneClient(auth)
    client.authenticate()
    print("Authentication successful!")
except Exception as e:
    print(f"Error during authentication: {type(e).__name__} - {e}")
