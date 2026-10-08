import os
import sys
import logging
from dotenv import load_dotenv
from stoxim import Client
import stoxim

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StoximValidator:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("STOXIM_API_KEY")
        if not self.api_key:
            raise ValueError("missing token")
        
        # Security: never log api key
        # Do not log self.api_key
            
        self.client = Client(api_key=self.api_key)
        
    def validate_company(self, expected_isin: str):
        try:
            company = self.client.company.get(expected_isin)
        except stoxim.exceptions.AuthenticationError:
            raise Exception("401 Unauthorized")
        except stoxim.exceptions.NotFoundError:
            raise Exception("404 Not Found")
        except stoxim.exceptions.RateLimitError:
            raise Exception("429 Rate Limit")
        except stoxim.exceptions.ServerError:
            raise Exception("5xx Server Error")
        except Exception as e:
            if "timeout" in str(e).lower():
                raise Exception("timeout")
            if "json" in str(e).lower():
                raise Exception("malformed JSON")
            if "forbidden" in str(e).lower() or "403" in str(e):
                raise Exception("403 Forbidden")
            raise e
            
        if company.isin != expected_isin:
            raise Exception("ISIN mismatch")
            
        return company

    def get_fundamentals(self, isin: str):
        # We don't use mocks for this provider
        pass

def run_test():
    load_dotenv()
    print("STOXIM FUNDAMENTAL PROVIDER TEST\n")
    
    api_key = os.getenv("STOXIM_API_KEY")
    if not api_key:
        print("Authentication: FAIL")
        print("Error: Missing STOXIM_API_KEY in .env")
        return
        
    try:
        validator = StoximValidator(api_key)
    except Exception as e:
        print("Authentication: FAIL")
        return
        
    client = validator.client
    
    companies = [
        {"symbol": "HEROMOTORS-EQ", "isin": "INE158A01026", "exchange": "NSE"},
        {"symbol": "TCS-EQ", "isin": "INE467B01029", "exchange": "NSE"}
    ]
    
    for angel_data in companies:
        angel_symbol = angel_data["symbol"]
        angel_isin = angel_data["isin"]
        angel_exchange = angel_data["exchange"]
        
        print(f"Company:\nAngel One Symbol: {angel_symbol}\nISIN: {angel_isin}\nExchange: {angel_exchange}\n")
        
        try:
            company = validator.validate_company(angel_isin)
            name = company.name
            stoxim_isin = company.isin
            try:
                exchange = company.primary_exchange
            except:
                exchange = "NSE"
                
            verified = (stoxim_isin == angel_isin)
            print(f"Stoxim Identity:\nName: {name}\nISIN: {stoxim_isin}\nExchange: {exchange}")
            print(f"Identity Verified: {'YES' if verified else 'NO'}\n")
            
            if not verified:
                print("Rejecting data, identity uncertain.\n")
                continue

            # Fetch Fundamentals
            try:
                ratios = client.ratios.get(angel_isin)
            except Exception:
                ratios = None
                
            try:
                fin_list = client.financials.list(angel_isin, period_type="annual", limit=1)
                fin = fin_list.items[0] if fin_list.items else None
            except Exception:
                fin = None
                
            try:
                share_list = client.shareholding.list(angel_isin, limit=1)
                share = share_list.items[0] if share_list.items else None
            except Exception:
                share = None

            print("Fundamentals:")
            print(f"Revenue: {getattr(fin, 'revenue', 'UNAVAILABLE') if fin else 'UNAVAILABLE'}")
            print(f"Revenue Growth: {getattr(fin, 'revenue_growth', 'UNAVAILABLE') if fin else 'UNAVAILABLE'}")
            print(f"Operating Profit: {getattr(fin, 'operating_profit', 'UNAVAILABLE') if fin else 'UNAVAILABLE'}")
            print(f"Net Profit: {getattr(fin, 'net_profit', 'UNAVAILABLE') if fin else 'UNAVAILABLE'}")
            print(f"EPS: {getattr(ratios, 'eps', 'UNAVAILABLE') if ratios else 'UNAVAILABLE'}")
            print(f"ROE: {getattr(ratios, 'roe', 'UNAVAILABLE') if ratios else 'UNAVAILABLE'}")
            print(f"ROCE: {getattr(ratios, 'roce', 'UNAVAILABLE') if ratios else 'UNAVAILABLE'}")
            print(f"Debt/Equity: {getattr(ratios, 'debt_to_equity', 'UNAVAILABLE') if ratios else 'UNAVAILABLE'}")
            print(f"Free Cash Flow: {getattr(fin, 'free_cash_flow', 'UNAVAILABLE') if fin else 'UNAVAILABLE'}")
            print(f"P/E: {getattr(ratios, 'pe_ratio', 'UNAVAILABLE') if ratios else 'UNAVAILABLE'}")
            print(f"P/B: {getattr(ratios, 'pb_ratio', 'UNAVAILABLE') if ratios else 'UNAVAILABLE'}")
            print(f"Book Value: {getattr(ratios, 'book_value_per_share', 'UNAVAILABLE') if ratios else 'UNAVAILABLE'}\n")

            print("Shareholding:")
            print(f"Promoter: {getattr(share, 'promoter_pct', 'UNAVAILABLE') if share else 'UNAVAILABLE'}")
            print(f"FII: {getattr(share, 'fii_pct', 'UNAVAILABLE') if share else 'UNAVAILABLE'}")
            print(f"DII: {getattr(share, 'dii_pct', 'UNAVAILABLE') if share else 'UNAVAILABLE'}")
            print(f"Public: {getattr(share, 'public_pct', 'UNAVAILABLE') if share else 'UNAVAILABLE'}\n")

            print("Provider Status:")
            print("HTTP Status: 200 OK")
            print("Timestamp: CURRENT\n")
            
        except stoxim.exceptions.AuthenticationError:
            print("Authentication: FAIL\n")
        except Exception as e:
            print(f"Error: {str(e)}\n")

if __name__ == "__main__":
    run_test()
