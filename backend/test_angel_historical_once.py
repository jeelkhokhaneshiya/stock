import os
import sys
import logging
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.services.brokers.angel_one.auth import AngelOneAuth
from app.services.brokers.angel_one.client import AngelOneClient
from app.services.brokers.angel_one.exceptions import AngelOneInvalidResponseError, AngelOneAuthenticationError

logging.basicConfig(level=logging.ERROR) # Only show our explicit prints

from app.services.market_data.angel_one import AngelOneMarketDataProvider

def main():
    print("="*50)
    print("DIAGNOSTIC: ANGEL ONE HISTORICAL DATA (ONCE)")
    print("="*50)

    try:
        auth = AngelOneAuth(
            client_id=settings.ANGEL_ONE_CLIENT_ID,
            password=settings.ANGEL_ONE_PASSWORD,
            api_key=settings.ANGEL_ONE_API_KEY,
            totp_secret=settings.ANGEL_ONE_TOTP_SECRET
        )
        client = AngelOneClient(auth=auth)
        client.authenticate()
        print("1. Authentication Status: SUCCESS")
    except Exception as e:
        print(f"1. Authentication Status: FAILED ({e})")
        return

    provider = AngelOneMarketDataProvider(client)
    symbol = "HEROMOTORS-EQ"
    token = provider._get_token(symbol, "NSE")
    print(f"Resolved token for {symbol}: '{token}'")

    end_dt = datetime.now(timezone.utc)
    timeframes = {
        "FIVE_MINUTE": 5,
        "FIFTEEN_MINUTE": 10,
        "ONE_HOUR": 60,
        "ONE_DAY": 365
    }

    for interval, days in timeframes.items():
        start_dt = end_dt - timedelta(days=days)
        payload = {
            "exchange": "NSE",
            "symboltoken": token,
            "interval": interval,
            "fromdate": start_dt.strftime("%Y-%m-%d %H:%M"),
            "todate": end_dt.strftime("%Y-%m-%d %H:%M")
        }

        try:
            print(f"\nRequesting Historical Data for {symbol} (Token: {token}) Interval: {interval}...")
            res = client.get_candle_data(payload)
            
            # In case the payload has an error status but doesn't raise exception
            if isinstance(res, dict) and not res.get("status", True):
                print(f"2. HTTP/API Status: ERROR")
                print(f"3. Error Code/Message: {res.get('errorcode')} - {res.get('message')}")
                print(f"4. Candle Data Returned: NO")
                print(f"5. Number of Candles: 0")
            else:
                print("2. HTTP/API Status: SUCCESS")
                print("3. Error Code/Message: None")
                
                # Note: Depending on the API format and our wrapper, res might be the array itself
                data_list = res if isinstance(res, list) else res.get("data", [])
                has_data = len(data_list) > 0
                
                print(f"4. Candle Data Returned: {'YES' if has_data else 'NO (Empty)'}")
                print(f"5. Number of Candles: {len(data_list)}")
                
                if has_data:
                    print("\nStatus: HISTORICAL_DATA_OK")
                else:
                    print("\nStatus: HISTORICAL_DATA_EMPTY")
                    
        except AngelOneInvalidResponseError as e:
            err_msg = str(e).lower()
            if "403" in err_msg or "permissions denied" in err_msg:
                print(f"2. HTTP/API Status: 403 FORBIDDEN")
                print(f"3. Error Code/Message: {e}")
                print("4. Candle Data Returned: NO")
                print("5. Number of Candles: 0")
                print("\nStatus: HISTORICAL_DATA_403")
            else:
                print(f"2. HTTP/API Status: INVALID RESPONSE")
                print(f"3. Error Code/Message: {e}")
                print("4. Candle Data Returned: NO")
                print("5. Number of Candles: 0")
                print("\nStatus: ERROR")
                
        except AngelOneAuthenticationError as e:
            print(f"2. HTTP/API Status: AUTHENTICATION ERROR")
            print(f"3. Error Code/Message: {e}")
            print("4. Candle Data Returned: NO")
            print("5. Number of Candles: 0")
            print("\nStatus: ERROR")
            
        except Exception as e:
            print(f"2. HTTP/API Status: UNKNOWN EXCEPTION")
            print(f"3. Error Code/Message: {e}")
            print("4. Candle Data Returned: NO")
            print("5. Number of Candles: 0")
            print("\nStatus: ERROR")
            
        print("-" * 50)

if __name__ == "__main__":
    main()
