import sys
import os
import argparse
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
load_dotenv()

from app.core.config import settings
from app.services.brokers.angel_one.auth import AngelOneAuth
from app.services.brokers.angel_one.client import AngelOneClient
from app.services.market_data.angel_one import AngelOneMarketDataProvider

def main():
    print("==================================================")
    print("DIAGNOSTIC: ANGEL ONE SMARTAPI FUNDAMENTAL VALIDATION")
    print("==================================================")
    
    auth = AngelOneAuth(
        api_key=settings.ANGEL_ONE_API_KEY,
        client_id=settings.ANGEL_ONE_CLIENT_ID,
        password=settings.ANGEL_ONE_PASSWORD,
        totp_secret=settings.ANGEL_ONE_TOTP_SECRET
    )
    client = AngelOneClient(auth=auth)
    
    try:
        authenticated = client.authenticate()
        print(f"Angel One Authentication: {'SUCCESS' if authenticated else 'FAIL'}")
    except Exception as e:
        print(f"Angel One Authentication: FAIL ({e})")
        sys.exit(1)

    provider = AngelOneMarketDataProvider(client=client)

    companies = [
        {"name": "Hero MotoCorp", "symbol": "HEROMOTOCO-EQ", "isin": "INE158A01026"},
        {"name": "TCS", "symbol": "TCS-EQ", "isin": "INE467A01029"}
    ]

    for company in companies:
        print(f"\nTesting {company['name']} (Symbol: {company['symbol']}, ISIN: {company['isin']})...")
        
        # We test get_fundamentals which we know returns None for Angel One
        fundamentals = provider.get_fundamentals(company["symbol"], "NSE", company["isin"])
        
        if fundamentals is None:
            print("\nFinancials:")
            print("  Revenue: UNAVAILABLE")
            print("  Revenue Growth: UNAVAILABLE")
            print("  Operating Profit: UNAVAILABLE")
            print("  Net Profit: UNAVAILABLE")
            print("  EPS: UNAVAILABLE")
            print("  EPS Growth: UNAVAILABLE")
            print("\nKey Ratios:")
            print("  P/E: UNAVAILABLE")
            print("  P/B (Book Value): UNAVAILABLE")
            print("  ROE: UNAVAILABLE")
            print("  ROCE: UNAVAILABLE")
            print("  Debt/Equity: UNAVAILABLE")
            print("\nShareholding:")
            print("  Promoter Holding: UNAVAILABLE")
            print("  Institutional Holding: UNAVAILABLE")
            print("  Public Holding: UNAVAILABLE")
            print("\nReason: Angel One SmartAPI officially DOES NOT provide a fundamental/financial data endpoint.")

    print("\n==================================================")
    print("OVERALL STATUS: UNAVAILABLE")
    print("Angel One SmartAPI is strictly a trading, portfolio, and market data API.")
    print("It does not provide balance sheets, income statements, or detailed financial ratios.")
    print("==================================================")

if __name__ == "__main__":
    main()
