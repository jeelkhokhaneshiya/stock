import os
import sys
import logging
import json
from app.core.config import settings
from app.services.brokers.angel_one.auth import AngelOneAuth
from app.services.brokers.angel_one.client import AngelOneClient
from app.services.brokers.angel_one.data_service import AngelOneDataService
from app.services.portfolio.portfolio_manager import PortfolioManager

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("CLI")

def print_header(title: str):
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)

def main():
    print_header("ANGEL ONE - READ-ONLY INVESTMENT SYSTEM (CLI)")
    print("HARD STOP: No orders will be executed. Read-only analysis phase.\n")
    
    # Block live execution explicitly
    os.environ["ENABLE_LIVE_TRADING"] = "false"
    os.environ["LIVE_EXECUTION_UNLOCKED"] = "false"
    os.environ["BROKER_EXECUTION_BLOCKED"] = "true"
    
    # Ensure real data provider is used
    os.environ["MARKET_DATA_PROVIDER"] = "angelone"
    settings.MARKET_DATA_PROVIDER = "angelone"
    
    print("[1] Initializing broker connection...")
    try:
        # Load auth from environment/settings
        client_id = settings.ANGEL_ONE_CLIENT_ID
        password = settings.ANGEL_ONE_PASSWORD
        api_key = settings.ANGEL_ONE_API_KEY
        totp_secret = settings.ANGEL_ONE_TOTP_SECRET
        
        if not all([client_id, password, api_key, totp_secret]):
            print("\nERROR: Angel One credentials missing in environment.")
            print("Please set ANGEL_ONE_CLIENT_ID, ANGEL_ONE_PASSWORD, ANGEL_ONE_API_KEY, ANGEL_ONE_TOTP_SECRET")
            sys.exit(1)
            
        auth = AngelOneAuth(
            client_id=client_id,
            password=password,
            api_key=api_key,
            totp_secret=totp_secret
        )
        client = AngelOneClient(auth=auth)
        import app.api.deps
        app.api.deps._global_angel_one_client = client
        
        print("[2] Authenticating (Single Session)...")
        try:
            client.authenticate()
        except Exception as e:
            print(f"BROKER_DISCONNECTED: Could not authenticate with Angel One: {e}")
            sys.exit(1)
            
        print("[3] Fetching real data & Running Decision Engine...")
        data_svc = AngelOneDataService(client)
        manager = PortfolioManager(client=data_svc)
        
        # This orchestrates fetching funds, holdings, positions, and running the analyzers
        analysis = manager.get_full_portfolio_analysis()
        
        if analysis.get("status") != "OK":
            print(f"\nERROR: Analysis failed. Reason: {analysis.get('reason')}")
            sys.exit(1)
            
        summary = analysis.get("portfolio_summary", {})
        print_header("PORTFOLIO STATUS")
        print(f"Available Cash: INR {summary.get('cash_available', 0)}")
        print(f"Total Portfolio Value: INR {summary.get('total_portfolio_value', 0)}")
        print(f"Total PnL: INR {summary.get('total_pnl', 0)}")
        
        print_header("DECISION ENGINE REPORT (HOLDINGS & CANDIDATES)")
        action_plan = analysis.get("daily_investment_action_plan", [])
        
        if not action_plan:
            print("No actionable decisions generated.")
        
        for item in action_plan:
            symbol = item.get("symbol", "UNKNOWN")
            action = item.get("action", "NO_ACTION")
            qty = item.get("quantity", 0)
            curr_qty = item.get("current_quantity", 0)
            ltp = item.get("current_price", 0.0)
            est_val = item.get("estimated_value", 0.0)
            pnl_pct = item.get("pnl_pct", 0.0)
            confidence = item.get("confidence", 0.0)
            risk = item.get("risk_score", 0.0)
            reasons = item.get("reasons", [])
            
            print(f"\n[{action}] {symbol}")
            print(f"  Current Qty : {curr_qty} | Target Qty Diff: {qty} | Current Price: INR {ltp}")
            if action in ["BUY", "BUY_MORE"]:
                print(f"  Est. Investment: INR {est_val}")
            elif action in ["SELL", "REDUCE"]:
                print(f"  Est. Proceeds  : INR {est_val}")
            print(f"  P&L %       : {pnl_pct}%")
            print(f"  Confidence  : {confidence*100:.1f}% | Risk Score: {risk}/100")
            print(f"  Reasoning   : {'; '.join(reasons)}")
            
        print_header("ORDER PREVIEW")
        print("WAITING FOR USER CONFIRMATION (Read-Only Mode active)")
        print("\nNote: Execution guards remain ACTIVE. No real-money orders are submitted.")
        
    except Exception as e:
        print(f"System Error: {e}")
        import traceback
        traceback.print_exc()
        
if __name__ == "__main__":
    main()
