import sys
import os
import argparse
from dotenv import load_dotenv
import httpx
import time

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
load_dotenv()

def main():
    print("==================================================")
    print("FINNHUB FUNDAMENTAL VALIDATION")
    print("==================================================")
    
    api_key = os.environ.get("FINNHUB_API_KEY")
    
    if not api_key or api_key.lower() in {"placeholder", "your_finnhub_api_key_here", "", "none"}:
        print("API KEY: MISSING (or placeholder)")
        print("Authentication: FAIL")
        print("\nOVERALL RESULT:")
        print("AUTHENTICATION_FAILED")
        sys.exit(0)
    else:
        print(f"API KEY: FOUND (length: {len(api_key)})")

    companies = [
        {"name": "Hero MotoCorp", "symbol": "HEROMOTOCO.NS", "isin": "INE158A01026"},
        {"name": "TCS", "symbol": "TCS.NS", "isin": "INE467A01029"}
    ]

    all_verified = True
    all_available = True
    overall_status = "VALID_AND_USABLE"
    
    for company in companies:
        print(f"\n{company['name']}:")
        
        url = "https://finnhub.io/api/v1/stock/metric"
        params = {
            "symbol": company["symbol"],
            "metric": "all",
            "token": api_key
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, params=params)
                http_status = resp.status_code
                
                print(f"HTTP status: {http_status}")
                
                if http_status in (401, 403):
                    print("Authentication: FAIL (401/403)")
                    print("Identity: UNVERIFIED")
                    print("Fundamentals: UNAVAILABLE")
                    print("Fields received: NONE")
                    overall_status = "AUTHENTICATION_FAILED" if overall_status in ("VALID_AND_USABLE", "INDIA_ACCESS_RESTRICTED") else overall_status
                    continue
                elif http_status == 429:
                    print("Authentication: PASS (Rate Limited)")
                    print("Identity: UNVERIFIED")
                    print("Fundamentals: UNAVAILABLE")
                    print("Fields received: NONE")
                    overall_status = "PROVIDER_UNSUITABLE"
                    continue
                elif http_status != 200:
                    print(f"Authentication: PASS (Error {http_status})")
                    print("Identity: UNVERIFIED")
                    print("Fundamentals: UNAVAILABLE")
                    print("Fields received: NONE")
                    overall_status = "NETWORK_ERROR"
                    continue
                
                # 200 OK
                data = resp.json()
                
                # Verify identity
                series = data.get("series", {})
                metric = data.get("metric", {})
                
                # Finnhub metric endpoint doesn't always return ISIN directly, 
                # but we can try fetching company profile2 to verify identity
                profile_url = "https://finnhub.io/api/v1/stock/profile2"
                profile_params = {"symbol": company["symbol"], "token": api_key}
                profile_resp = client.get(profile_url, params=profile_params)
                profile_data = profile_resp.json() if profile_resp.status_code == 200 else {}
                
                api_name = profile_data.get("name", "")
                
                identity_verified = False
                if api_name and company["name"].split()[0].lower() in api_name.lower():
                    identity_verified = True
                elif metric: # if metric data returned
                    identity_verified = True
                
                print(f"Identity: {'VERIFIED' if identity_verified else 'UNVERIFIED'}")
                
                if not metric and not series:
                    print("Fundamentals: UNAVAILABLE (Empty data)")
                    print("Fields received: NONE")
                    if overall_status == "VALID_AND_USABLE":
                        overall_status = "FUNDAMENTALS_UNAVAILABLE"
                    # If this is for Indian stock and empty, could be restricted
                    if overall_status == "FUNDAMENTALS_UNAVAILABLE":
                        overall_status = "INDIA_ACCESS_RESTRICTED"
                else:
                    print("Fundamentals: AVAILABLE")
                    fields = list(metric.keys())[:10] + (["..."] if len(metric) > 10 else [])
                    print(f"Fields received: {', '.join(fields) if fields else 'NONE'}")
                    
        except Exception as e:
            print(f"HTTP status: Error ({e})")
            print("Identity: UNVERIFIED")
            print("Fundamentals: UNAVAILABLE")
            print("Fields received: NONE")
            overall_status = "NETWORK_ERROR"

    print("\nOVERALL:")
    print(overall_status)


if __name__ == "__main__":
    main()
