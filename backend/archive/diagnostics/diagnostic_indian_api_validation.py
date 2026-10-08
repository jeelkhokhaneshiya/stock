import sys
import os
import argparse
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
load_dotenv()

from app.services.fundamentals.indian_api import IndianAPIFundamentalDataProvider
from app.services.fundamentals.base import FundamentalProviderStatus

def main():
    print("==================================================")
    print("INDIAN API KEY VALIDATION")
    print("==================================================")
    
    api_key = os.environ.get("INDIAN_API_KEY")
    
    if not api_key or api_key.lower() in {"placeholder", "your_indian_api_key_here", "", "none"}:
        print("API KEY: MISSING (or placeholder)")
        print("Authentication: FAIL")
        print("\nOVERALL RESULT:")
        print("AUTHENTICATION_FAILED")
        sys.exit(0)
    else:
        print(f"API KEY: FOUND (length: {len(api_key)})")

    provider = IndianAPIFundamentalDataProvider(api_key=api_key)

    companies = [
        {"name": "Hero MotoCorp", "symbol": "HEROMOTOCO-EQ", "isin": "INE158A01026"},
        {"name": "TCS", "symbol": "TCS-EQ", "isin": "INE467A01029"}
    ]

    all_verified = True
    all_available = True
    overall_status = "VALID_AND_USABLE"
    
    for company in companies:
        print(f"\n{company['name']}:")
        
        result = provider.get_fundamentals(company["symbol"], "NSE", company["isin"])
        
        auth_pass = result.status not in (FundamentalProviderStatus.AUTH_ERROR, FundamentalProviderStatus.FORBIDDEN)
        print(f"Authentication: {'PASS' if auth_pass else 'FAIL'}")
        
        id_verified = getattr(result, "identity_verified", False)
        print(f"Company identity: {'VERIFIED' if id_verified else 'UNVERIFIED'}")
        
        fundamentals_avail = result.status == FundamentalProviderStatus.AVAILABLE
        print(f"Fundamentals: {'AVAILABLE' if fundamentals_avail else 'UNAVAILABLE'}")
        
        avail_fields = getattr(result, "available_fields", [])
        if avail_fields:
            print(f"Fields received: {', '.join(avail_fields)}")
        else:
            print("Fields received: NONE")
            
        print(f"HTTP status: {result.http_status}")
        
        if not auth_pass:
            overall_status = "AUTHENTICATION_FAILED"
        elif result.status == FundamentalProviderStatus.NOT_FOUND:
            overall_status = "NETWORK/ENDPOINT_ERROR" if overall_status == "VALID_AND_USABLE" else overall_status
        elif not fundamentals_avail:
            overall_status = "FUNDAMENTALS_UNAVAILABLE" if overall_status == "VALID_AND_USABLE" else overall_status
        
        if not id_verified or not fundamentals_avail:
            all_verified = False

    print("\nOVERALL RESULT:")
    if overall_status == "VALID_AND_USABLE" and all_verified:
        print("VALID_AND_USABLE")
    else:
        if overall_status == "VALID_AND_USABLE":
            print("PROVIDER_UNSUITABLE") # Authentication passed, but identity failed or missing required fields
        else:
            print(overall_status)

if __name__ == "__main__":
    main()
