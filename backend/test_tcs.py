from app.services.market_data.angel_one import AngelOneMarketDataProvider
from unittest.mock import MagicMock

def test():
    md = AngelOneMarketDataProvider(MagicMock())
    token = md._get_token("TCS", "NSE")
    print(f"Token resolved: '{token}'")
    
    # print what exists in the map for TCS
    for k, v in md._master_mapping.items():
        if "TCS" in k:
            print(f"{k} -> {v}")
            
if __name__ == "__main__":
    test()
