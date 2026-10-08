import os
import sys
import asyncio
from app.core.config import settings
from app.services.brokers.angel_one.auth import AngelOneAuth
from app.services.brokers.angel_one.client import AngelOneClient
from app.services.market_data.angel_one import AngelOneMarketDataProvider
from app.services.fundamentals.screener import ScreenerFundamentalDataProvider

async def main():
    print("=== REAL-DATA SMOKE TEST ===")
    
    # 1. Angel One Auth & Client
    client_id = settings.ANGEL_ONE_CLIENT_ID
    password = settings.ANGEL_ONE_PASSWORD
    api_key = settings.ANGEL_ONE_API_KEY
    totp_secret = settings.ANGEL_ONE_TOTP_SECRET
    
    if not all([client_id, password, api_key, totp_secret]):
        print("FAIL: Missing Angel One credentials in environment")
        return
        
    print("1. Angel One Authentication...")
    try:
        auth = AngelOneAuth(
            api_key=api_key,
            client_id=client_id,
            password=password,
            totp_secret=totp_secret,
        )
        client = AngelOneClient(auth=auth)
        client.authenticate()
        print("   PASS")
    except Exception as e:
        print(f"   FAIL: {e}")
        return
        
    print("\n2. Real Cash Test (RMS)...")
    try:
        rms = client.get_rms()
        cash = rms.get("availablecash", 0)
        print(f"   PASS: Available Cash: {cash}")
    except Exception as e:
        print(f"   FAIL: {e}")
        
    print("\n3. Real Holdings Test...")
    try:
        holdings = client.get_holdings()
        count = len(holdings) if isinstance(holdings, list) else 0
        print(f"   PASS: Retrieved {count} holdings")
    except Exception as e:
        print(f"   FAIL: {e}")
        
    print("\n4. Real Market-Data Test...")
    try:
        md = AngelOneMarketDataProvider(client)
        quote = md.get_quote("TCS", "NSE")
        if quote and quote.price > 0 and quote.symbol == "TCS" and quote.exchange == "NSE" and quote.data_source == "ANGEL_ONE":
            print(f"   PASS: Retrieved real quote for TCS (LTP: INR {quote.price})")
        else:
            print("   FAIL: Could not retrieve market quote for TCS or data invalid")
    except Exception as e:
        print(f"   FAIL: {e}")
        
    print("\n5. Screener Real Fundamentals Test...")
    try:
        screener = ScreenerFundamentalDataProvider()
        fundamentals = screener.get_fundamentals("TCS", "NSE")
        if fundamentals.identity_verified:
            print(f"   PASS: Retrieved Screener data for TCS (PE: {fundamentals.pe_ratio})")
        else:
            print("   FAIL: Screener identity not verified")
    except Exception as e:
        print(f"   FAIL: {e}")

if __name__ == "__main__":
    asyncio.run(main())
