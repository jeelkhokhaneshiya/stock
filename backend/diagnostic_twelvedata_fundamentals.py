import sys
import os
import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
load_dotenv()

def test_endpoint(client, base_url, endpoint, api_key, symbol, exchange):
    params = {
        "symbol": symbol,
        "exchange": exchange,
        "apikey": api_key
    }
    
    url = f"{base_url}/{endpoint}"
    try:
        resp = client.get(url, params=params)
        
        status_code = resp.status_code
        data = None
        try:
            data = resp.json()
        except:
            pass
            
        if status_code != 200:
            msg = data.get("message", "No message") if data else resp.text
            return f"FAIL (HTTP {status_code}: {msg})"
            
        if "status" in data and data["status"] == "error":
            code = data.get("code")
            msg = data.get("message", "")
            return f"FAIL (API Error {code}: {msg})"
            
        data = resp.json()
        if "status" in data and data["status"] == "error":
            code = data.get("code")
            msg = data.get("message", "")
            return f"FAIL (API Error {code}: {msg})"
            
        return f"SUCCESS (Fields: {len(data)})"
    except Exception as e:
        return f"FAIL (Exception: {str(e)})"

def main():
    print("==================================================")
    print("TWELVE DATA FUNDAMENTAL VALIDATION")
    print("==================================================")
    
    api_key = os.environ.get("TWELVE_DATA_API_KEY")
    
    if not api_key or api_key.lower() in {"placeholder", "", "none"}:
        print("Environment:\nMISSING")
        print("\nREAL FUNDAMENTAL DATA:\nNO")
        print("\nAPI PLAN SUFFICIENT:\nUNKNOWN")
        print("\nINDIA/NSE ACCESS:\nUNKNOWN")
        print("\nPRODUCTION READY:\nNO")
        return
        
    print(f"Environment:\nFOUND (length: {len(api_key)})")

    companies = [
        {"name": "Hero MotoCorp", "symbol": "HEROMOTOCO", "exchange": "NSE", "isin": "INE158A01026"},
        {"name": "TCS", "symbol": "TCS", "exchange": "NSE", "isin": "INE467A01029"}
    ]

    base_url = "https://api.twelvedata.com"
    endpoints = ["profile", "statistics", "income_statement", "balance_sheet", "cash_flow", "earnings"]
    
    client = httpx.Client(timeout=10.0)
    
    plan_sufficient = False
    india_access = False
    real_data = False
    
    for company in companies:
        print(f"\n{company['name']}:")
        print(f"Symbol: {company['symbol']}:{company['exchange']}")
        
        overall = "SUCCESS"
        reason = ""
        identity = "UNVERIFIED"
        
        # Test profile for identity
        profile_params = {"symbol": company["symbol"], "exchange": company["exchange"], "apikey": api_key}
        resp = client.get(f"{base_url}/profile", params=profile_params)
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "error":
                prof_res = f"FAIL ({data.get('message')})"
                overall = "FAIL"
                reason = data.get('code', 'ERROR')
            else:
                prof_res = "SUCCESS"
                api_name = data.get("name", "")
                if api_name and company["name"].split()[0].lower() in api_name.lower():
                    identity = "VERIFIED"
                india_access = True
        else:
            prof_res = f"FAIL (HTTP {resp.status_code})"
            overall = "FAIL"
            reason = f"HTTP {resp.status_code}"
            
        print(f"Profile: {prof_res}")
        
        for ep in endpoints[1:]:
            res = test_endpoint(client, base_url, ep, api_key, company["symbol"], company["exchange"])
            print(f"{ep.replace('_', ' ').title()}: {res}")
            if "SUCCESS" in res:
                plan_sufficient = True
                real_data = True
            elif "401" in res or "403" in res or "429" in res:
                overall = "FAIL"
                reason = "PLAN_RESTRICTED"
                plan_sufficient = False

        print(f"Identity: {identity}")
        print(f"Overall: {overall}")
        print(f"Reason: {reason if reason else 'OK'}")

    print("\nREAL FUNDAMENTAL DATA:")
    print("YES" if real_data else "NO")

    print("\nAPI PLAN SUFFICIENT:")
    print("YES" if plan_sufficient else "NO")

    print("\nINDIA/NSE ACCESS:")
    print("YES" if india_access else "NO")

    print("\nPRODUCTION READY:")
    print("YES" if (real_data and plan_sufficient and india_access) else "NO")

if __name__ == "__main__":
    main()
