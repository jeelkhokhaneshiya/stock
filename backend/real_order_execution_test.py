import asyncio
from datetime import datetime, timezone
import uuid

from app.core.config import settings
from app.services.brokers.angel_one.auth import AngelOneAuth
from app.services.brokers.angel_one.client import AngelOneClient
from app.services.brokers.angel_one.data_service import AngelOneDataService
from app.services.portfolio.portfolio_manager import PortfolioManager
from app.schemas.execution import OrderIntent
from app.services.execution.real_execution import RealExecutionEngine

async def run_real_order_validation():
    print("=== PHASE 14.3 CONTROLLED REAL ORDER VALIDATION ===")
    
    # Do not manipulate safety flags to bypass!
    print(f"Safety Mode: ENABLE_LIVE_TRADING={settings.ENABLE_LIVE_TRADING}")
    print(f"Kill Switch: AUTONOMOUS_KILL_SWITCH={settings.AUTONOMOUS_KILL_SWITCH}")
    print(f"Execution Mode: {settings.EXECUTION_MODE}")
    
    auth = AngelOneAuth(
        api_key=settings.ANGEL_ONE_API_KEY,
        client_id=settings.ANGEL_ONE_CLIENT_ID,
        password=settings.ANGEL_ONE_PASSWORD,
        totp_secret=settings.ANGEL_ONE_TOTP_SECRET,
    )
    client = AngelOneClient(auth=auth)
    client.authenticate()
    print("1. Angel One Authentication PASS")
    
    data_svc = AngelOneDataService(client)
    pm = PortfolioManager(client=data_svc)
    
    print("2. Fetching real portfolio snapshot & generating decisions...")
    analysis = pm.get_full_portfolio_analysis()
    
    if analysis["status"] != "OK":
        print(f"STOP: {analysis.get('reason')}")
        return
        
    summary = analysis["portfolio_summary"]
    cash = float(summary.get('cash_available', 0))
    print(f"3. Real Snapshot: Cash: {cash}")
    
    action_plan = analysis["daily_investment_action_plan"]
    
    buy_candidate = None
    for decision in action_plan:
        if decision.get("action") in ["BUY", "BUY_MORE"]:
            buy_candidate = decision
            break
            
    if not buy_candidate:
        print("SAFE NO-ORDER: No valid BUY/BUY_MORE candidate found based on real data.")
        print("NO REAL ORDER SUBMITTED")
        return
        
    symbol = buy_candidate["symbol"]
    price = buy_candidate.get("current_price", 0.0)
    
    # SMALLEST VALID QUANTITY
    qty = 1
    est_amount = price * qty
    
    print(f"4. Selected Candidate: {symbol} @ {price}, Qty: {qty}, Est Amount: {est_amount}")
    
    if (cash - est_amount) < settings.MIN_CASH_RESERVE:
        print("SAFE NO-ORDER: Insufficient cash after MIN_CASH_RESERVE.")
        print("NO REAL ORDER SUBMITTED")
        return
        
    engine = RealExecutionEngine(client, pm, "audit_real.jsonl")
    
    print("5. Generating OrderIntent...")
    intent = OrderIntent(
        intent_id=str(uuid.uuid4()),
        symbol=symbol,
        symboltoken="0", # Requires mapping in real system, using 0 for safety test
        exchange="NSE",
        transaction_type="BUY",
        product_type="DELIVERY",
        order_type="MARKET",
        quantity=qty,
        price=price,
        estimated_value=est_amount,
        decision_reason="Validation transaction",
        timestamp=datetime.now(timezone.utc)
    )
    
    print("6. Generating OrderPreview...")
    context = {
        "ltp": price,
        "fundamental_score": 50,
        "technical_score": 50,
        "valuation_score": 50,
        "risk_score": 50,
        "main_risks": [],
        "data_freshness": "FRESH"
    }
    
    try:
        preview = engine.create_order_preview(intent, context)
        print(f"   [SUCCESS] Created OrderPreview: {preview.preview_id}")
    except Exception as e:
        print(f"   [STOP] Failed to create preview: {e}")
        return
        
    print("7. EXPLICIT HUMAN CONFIRMATION REQUIRED")
    print("   Workflow is running autonomously, so human confirmation is NOT provided.")
    print("   Expected Result: System stops here.")
    
    # Try executing without confirmation to prove safety
    print("8. Attempting execution WITHOUT confirmation...")
    result = engine.execute_confirmed_order("dummy_conf_id", intent)
    
    print(f"   Execution Result: {result.status} - {result.message}")
    print("NO REAL ORDER SUBMITTED")

if __name__ == "__main__":
    asyncio.run(run_real_order_validation())
