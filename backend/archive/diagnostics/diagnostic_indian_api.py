import os
import json
from dotenv import load_dotenv
from app.services.fundamentals.indian_api import IndianAPIFundamentalDataProvider

def run_diagnostic():
    load_dotenv()
    print("==================================================")
    print("DIAGNOSTIC: INDIAN API FUNDAMENTAL VALIDATION")
    print("==================================================")
    
    api_key = os.environ.get("INDIAN_API_KEY")
    if not api_key:
        print("API KEY STATUS: MISSING (UNAVAILABLE)")
    else:
        print(f"API KEY STATUS: FOUND ({len(api_key)} chars)")
        
    provider = IndianAPIFundamentalDataProvider()
    
    targets = [
        {"symbol": "HEROMOTOCO-EQ", "isin": "INE158A01026", "name": "Hero MotoCorp"},
        {"symbol": "TCS-EQ", "isin": "INE467A01029", "name": "TCS"},
    ]
    
    for t in targets:
        print("\n--------------------------------------------------")
        print(f"Testing {t['name']} (Symbol: {t['symbol']}, ISIN: {t['isin']})...")
        result = provider.get_fundamentals(symbol=t["symbol"], isin=t["isin"])
        
        print(f"Status: {result.status.value}")
        print(f"HTTP Status: {result.http_status}")
        print(f"Identity Verified: {result.identity_verified}")
        if result.error_message:
            print(f"Error Message: {result.error_message}")
            
        print("\nAvailable Fields received:")
        for f in result.available_fields:
            val = getattr(result, f)
            print(f"  - {f}: {val}")
            
        print("\nUnavailable Fields (Not provided by API):")
        print(f"  {', '.join(result.unavailable_fields) if result.unavailable_fields else 'None'}")

if __name__ == "__main__":
    run_diagnostic()
