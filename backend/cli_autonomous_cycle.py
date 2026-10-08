import os
import sys
import logging
from datetime import datetime, timezone
from app.core.config import settings
from app.services.brokers.angel_one.auth import AngelOneAuth
from app.services.brokers.angel_one.client import AngelOneClient
from app.services.brokers.angel_one.data_service import AngelOneDataService
from app.services.portfolio.portfolio_manager import PortfolioManager
import app.api.deps
from app.services.execution.readiness import ExecutionReadinessLayer, ExecutionReadinessError

logging.basicConfig(level=logging.ERROR) # Only show our prints

def run_cli_cycle():
    os.environ["ENABLE_LIVE_TRADING"] = "false"
    os.environ["LIVE_EXECUTION_UNLOCKED"] = "false"
    os.environ["BROKER_EXECUTION_BLOCKED"] = "true"
    os.environ["MARKET_DATA_PROVIDER"] = "angelone"
    settings.MARKET_DATA_PROVIDER = "angelone"

    print("="*40)
    print("AUTONOMOUS INVESTMENT CYCLE")
    print("="*40)
    print("Broker: Angel One")
    print("Data: REAL")
    print("Mode: READ-ONLY / DRY-RUN")
    print("Live Trading: DISABLED")
    print(f"Execution Blocked: {settings.BROKER_EXECUTION_BLOCKED}")
    print()

    try:
        auth = AngelOneAuth(
            client_id=settings.ANGEL_ONE_CLIENT_ID,
            password=settings.ANGEL_ONE_PASSWORD,
            api_key=settings.ANGEL_ONE_API_KEY,
            totp_secret=settings.ANGEL_ONE_TOTP_SECRET
        )
        client = AngelOneClient(auth=auth)
        client.authenticate()
        broker_status = "CONNECTED"
    except Exception as e:
        broker_status = "DISCONNECTED"
        print(f"Broker connection failed: {e}")
        return

    app.api.deps._global_angel_one_client = client
    data_svc = AngelOneDataService(client)
    manager = PortfolioManager(client=data_svc)
    readiness_layer = ExecutionReadinessLayer(manager, audit_log_path="order_intent_audit.jsonl")

    analysis = manager.get_full_portfolio_analysis()
    if analysis.get("status") != "OK":
        print(f"Analysis Failed: {analysis.get('reason')}")
        return
        
    summary = analysis.get("portfolio_summary", {})
    cash = summary.get("cash_available", 0)
    
    print(f"Available Cash: INR {cash}")
    
    holdings = analysis.get("holdings_analysis", [])
    print(f"Holdings: {len(holdings)}")
    
    candidates_count = analysis.get("candidates_analyzed_count", 0)
    print(f"Candidates Analyzed: {candidates_count}")
    
    print("\n" + "-"*40)
    print("DECISIONS")
    print("-"*40)

    action_plan = analysis.get("daily_investment_action_plan", [])
    
    decisions_grouped = {
        "BUY": [],
        "BUY_MORE": [],
        "HOLD": [],
        "REDUCE": [],
        "SELL": [],
        "WATCH": [],
        "NO_ACTION": []
    }
    
    for decision in action_plan:
        act = decision.get("action", "NO_ACTION")
        if act in decisions_grouped:
            decisions_grouped[act].append(decision)
            
    for act in ["BUY", "BUY_MORE", "HOLD", "REDUCE", "SELL", "WATCH"]:
        if not decisions_grouped[act]:
            continue
        print(f"\n{act}:")
        for d in decisions_grouped[act]:
            print(f"{d.get('symbol')}")
            if act in ["BUY", "BUY_MORE"]:
                print(f"Price: INR {d.get('current_price', 0)}")
                print(f"Qty: {d.get('quantity', 0)}")
                print(f"Amount: INR {d.get('estimated_value', 0)}")
            elif act in ["REDUCE", "SELL"]:
                print(f"Qty: {d.get('quantity', 0)}")
                print(f"Expected Value: INR {d.get('estimated_value', 0)}")
            print(f"Reason: {'; '.join(d.get('reasons', []))}")
            
    print("\n" + "-"*40)
    print("SAFETY")
    print("-"*40)
    
    kill_switch = "OK" if not settings.AUTONOMOUS_KILL_SWITCH else "ACTIVE"
    data_freshness = "OK" if analysis.get("data_freshness", {}).get("account_data") == "FRESH" else "WARNING"
    execution_blocked = "BLOCKED" if settings.BROKER_EXECUTION_BLOCKED else "UNBLOCKED"
    
    print(f"Kill Switch: {kill_switch}")
    print(f"Broker: {broker_status}")
    print(f"Data Freshness: {data_freshness}")
    print(f"Execution: {execution_blocked}")
    print("="*40)

if __name__ == "__main__":
    run_cli_cycle()
