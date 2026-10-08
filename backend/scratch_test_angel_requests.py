import sys
sys.path.append(r"d:\Jeel project\stock\backend")

from app.services.brokers.angel_one.auth import AngelOneAuth
from app.services.brokers.angel_one.client import AngelOneClient

import time

def test():
    auth = AngelOneAuth(
        api_key="HG9nKv2z",
        client_id="AAAG377380",
        password="1611",
        totp_secret="2Z2PJLPPPJJDPX2O3BKFFFHRUU",
    )
    client = AngelOneClient(auth)
    
    print("Authenticating...")
    client.authenticate()
    print("Authenticated successfully.")
    
    endpoints = [
        client.get_profile,
        client.get_rms,
        client.get_holdings,
        client.get_positions,
        client.get_order_book
    ]
    
    print("First batch of requests:")
    for ep in endpoints:
        try:
            ep()
            print(f"{ep.__name__} OK")
        except Exception as e:
            print(f"{ep.__name__} Failed: {type(e).__name__} - {e}")
            
    print("Sleeping for 5 seconds...")
    time.sleep(5)
    
    print("Second batch of requests:")
    for ep in endpoints:
        try:
            ep()
            print(f"{ep.__name__} OK")
        except Exception as e:
            print(f"{ep.__name__} Failed: {type(e).__name__} - {e}")

if __name__ == "__main__":
    test()
