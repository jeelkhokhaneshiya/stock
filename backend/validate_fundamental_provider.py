import sys
import os
import argparse
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
load_dotenv()

from app.services.fundamentals.base import (
    FundamentalProviderRegistry, 
    FundamentalProviderStatus
)
from app.services.fundamentals.fmp import FMPFundamentalDataProvider
from app.services.fundamentals.eodhd import EODHDFundamentalDataProvider
from app.services.fundamentals.indian_api import IndianAPIFundamentalDataProvider

def get_provider(name: str):
    name = name.lower()
    if name == "fmp":
        return FMPFundamentalDataProvider()
    elif name == "eodhd":
        return EODHDFundamentalDataProvider()
    elif name == "indian_api":
        return IndianAPIFundamentalDataProvider()
    else:
        raise ValueError(f"Unknown provider: {name}")

def main():
    parser = argparse.ArgumentParser(description="Validate a fundamental provider")
    parser.add_argument("provider", type=str, help="Name of the provider (fmp, eodhd, indian_api)")
    args = parser.parse_args()

    print("==================================================")
    print(f"DIAGNOSTIC: {args.provider.upper()} FUNDAMENTAL VALIDATION")
    print("==================================================")
    
    try:
        provider = get_provider(args.provider)
    except Exception as e:
        print(f"Error initializing provider: {e}")
        sys.exit(1)

    # We test Hero MotoCorp
    symbol = "HEROMOTORS-EQ"
    exchange = "NSE"
    isin = "INE158A01026"
    
    print(f"\nTesting Hero MotoCorp (Symbol: {symbol}, ISIN: {isin})...")
    
    try:
        result = provider.get_fundamentals(symbol, exchange, isin)
    except Exception as e:
        print(f"Provider crashed with error: {e}")
        sys.exit(1)

    result.calculate_confidence()

    print(f"\nAuthentication: {'PASS' if result.status != FundamentalProviderStatus.AUTH_ERROR else 'FAIL'}")
    print(f"Status: {result.status.name}")
    print(f"Coverage (NSE): {'PASS' if result.status != FundamentalProviderStatus.NOT_FOUND else 'FAIL'}")
    print(f"Identity Verified: {result.identity_verified} (Provider Symbol: {result.provider_ticker})")
    print(f"ISIN: {result.isin}")
    
    print("\nFinancials:")
    print(f"  Revenue: {result.revenue}")
    print(f"  Revenue Growth: {result.revenue_growth}")
    print(f"  Operating Profit: {result.operating_profit}")
    print(f"  Net Profit: {result.net_profit}")
    print(f"  EPS: {result.eps}")
    
    print("\nKey Ratios:")
    print(f"  P/E: {result.pe_ratio}")
    print(f"  P/B (Book Value): {result.book_value}")
    print(f"  ROE: {result.roe}")
    print(f"  Debt/Equity: {result.debt_to_equity}")
    print(f"  Free Cash Flow: {result.free_cash_flow}")

    print(f"\nFreshness / Period:")
    print(f"  Fetched At: {result.timestamp}")
    print(f"  Reporting Period: {result.reporting_period}")

    print(f"\nConfidence Score: {result.confidence:.2f}")
    
    overall = "PASS" if result.status == FundamentalProviderStatus.AVAILABLE and result.confidence > 0.2 else "FAIL"
    print(f"\nOverall Status: {overall}")

if __name__ == "__main__":
    main()
