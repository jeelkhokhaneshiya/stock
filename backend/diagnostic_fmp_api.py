import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
load_dotenv()

from app.services.fundamentals.fmp import FMPFundamentalDataProvider
from app.services.fundamentals.base import FundamentalProviderStatus

def print_result(company, symbol, isin, result):
    print(f"\n{'-'*50}")
    print(f"Testing {company} (Symbol: {symbol}, ISIN: {isin})...")
    
    if result.status == FundamentalProviderStatus.AVAILABLE:
        print("Status: PASS (AVAILABLE)")
        print(f"Identity Verified: {result.identity_verified} (FMP Symbol: {result.company_name} / {result.eodhd_ticker})")
        print(f"Fetched At: {result.timestamp}")
        
        print("\nIncome Statement:")
        print(f"  Revenue Growth: {result.revenue_growth}")
        print(f"  Profit Growth: {result.profit_growth}")
        print(f"  EPS: {result.eps}")
        
        print("\nCash Flow:")
        print(f"  Free Cash Flow: {result.free_cash_flow}")
        
        print("\nKey Ratios:")
        print(f"  P/E: {result.pe_ratio}")
        print(f"  P/B: {result.book_value}")
        print(f"  ROE: {result.roe}")
        print(f"  Debt/Equity: {result.debt_to_equity}")
    else:
        print(f"Status: FAIL ({result.status.name})")
        print("Identity Verified: False")
        print(f"Error: FMP returned {result.status.name} - {result.error_message or 'No specific message'}")

def main():
    print("==================================================")
    print("DIAGNOSTIC: FMP FUNDAMENTAL VALIDATION")
    print("==================================================")
    
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        print("FMP_API_KEY STATUS: MISSING")
        print("\nFMP_AUTH = BLOCKED_MISSING_KEY")
        print("\nCannot proceed with real data validation.")
        
        # We write a dummy validation report
        with open("FMP_VALIDATION_REPORT.md", "w") as f:
            f.write("# FMP VALIDATION REPORT\n\n")
            f.write("FMP_AUTH: BLOCKED_MISSING_KEY\n")
            f.write("HERO_MOTOCORP: FAIL\n")
            f.write("TCS: FAIL\n")
            f.write("ISIN_IDENTITY: FAIL\n")
            f.write("INCOME_STATEMENT: FAIL\n")
            f.write("BALANCE_SHEET: FAIL\n")
            f.write("CASH_FLOW: FAIL\n")
            f.write("KEY_RATIOS: FAIL\n")
            f.write("INDIAN_NSE_COVERAGE: FAIL\n")
            f.write("DATA_FRESHNESS: FAIL\n")
            f.write("OVERALL_PROVIDER: FAIL\n\n")
            f.write("Production integration: BLOCKED\n")
            
        return

    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
    print(f"FMP_API_KEY STATUS: FOUND (Masked: {masked_key})")
    
    provider = FMPFundamentalDataProvider()
    
    # 1. Hero MotoCorp
    result1 = provider.get_fundamentals("HEROMOTORS-EQ", "NSE", "INE158A01026")
    print_result("Hero MotoCorp", "HEROMOTORS-EQ", "INE158A01026", result1)
    
    # 2. TCS
    result2 = provider.get_fundamentals("TCS-EQ", "NSE", "INE467A01029")
    print_result("TCS", "TCS-EQ", "INE467A01029", result2)

if __name__ == "__main__":
    main()
