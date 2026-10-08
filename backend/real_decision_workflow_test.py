import asyncio
from datetime import datetime, timezone
import uuid

from app.core.config import settings
from app.services.brokers.angel_one.auth import AngelOneAuth
from app.services.brokers.angel_one.client import AngelOneClient
from app.services.brokers.angel_one.data_service import AngelOneDataService
from app.services.portfolio.portfolio_manager import PortfolioManager
from app.schemas.execution import OrderIntent, OrderPreview
from app.services.execution.real_execution import RealExecutionEngine

async def run_workflow():
    print("=== REAL INVESTMENT DECISION WORKFLOW ===")
    
    auth = AngelOneAuth(
        api_key=settings.ANGEL_ONE_API_KEY,
        client_id=settings.ANGEL_ONE_CLIENT_ID,
        password=settings.ANGEL_ONE_PASSWORD,
        totp_secret=settings.ANGEL_ONE_TOTP_SECRET,
    )
    client = AngelOneClient(auth=auth)
    client.authenticate()
    print("1. Authentication PASS")
    
    data_svc = AngelOneDataService(client)
    pm = PortfolioManager(client=data_svc)
    
    print("2. Fetching real portfolio snapshot & generating decisions...")
    analysis = pm.get_full_portfolio_analysis()
    
    if analysis["status"] != "OK":
        print(f"FAILED: {analysis.get('reason')}")
        return
        
    summary = analysis["portfolio_summary"]
    print(f"3. Snapshot: Cash: {summary.get('cash_available')}, Value: {summary.get('total_portfolio_value')}")
    
    action_plan = analysis["daily_investment_action_plan"]
    print(f"4. Generated {len(action_plan)} actionable decisions.")
    
    engine = RealExecutionEngine(client, pm, "audit.jsonl")
    intents = []
    previews = []
    
    for decision in action_plan:
        action = decision.get("action")
        if action in ["BUY", "BUY_MORE", "REDUCE", "SELL"]:
            print(f"  -> Processing actionable decision: {action} {decision['symbol']}")
            # Generate OrderIntent
            tx_type = "BUY" if action in ["BUY", "BUY_MORE"] else "SELL"
            qty = decision.get("quantity", 0)
            price = decision.get("current_price", 0.0)
            
            if qty > 0:
                intent = OrderIntent(
                    intent_id=str(uuid.uuid4()),
                    symbol=decision["symbol"],
                    symboltoken="0", # In real system, this is mapped
                    exchange="NSE",
                    transaction_type=tx_type,
                    product_type="DELIVERY",
                    order_type="MARKET",
                    quantity=qty,
                    price=price,
                    estimated_value=decision.get("estimated_value", qty*price),
                    decision_reason="; ".join(decision.get("reasons", [])),
                    timestamp=datetime.now(timezone.utc)
                )
                intents.append(intent)
                
                # Mock token mapping for preview since it doesn't matter for the preview generation itself
                # In real system this uses AngelOneMarketDataProvider mapping
                
                # RiskApproval Engine pass goes here (simulated as approved)
                
                # Create OrderPreview
                context = {
                    "ltp": price,
                    "fundamental_score": 50,
                    "technical_score": 50,
                    "valuation_score": 50,
                    "risk_score": decision.get("risk_score", 50),
                    "main_risks": decision.get("risks", []),
                    "data_freshness": decision.get("data_freshness", "FRESH")
                }
                
                try:
                    preview = engine.create_order_preview(intent, context)
                    previews.append(preview)
                    print(f"     [SUCCESS] Created OrderPreview: {preview.preview_id} for {qty} {decision['symbol']} @ {price} (Total: {preview.estimated_amount})")
                except Exception as e:
                    print(f"     [ERROR] Failed to create preview for {decision['symbol']}: {e}")
            else:
                print(f"     [SKIPPED] {action} {decision['symbol']} but quantity is 0 (likely insufficient cash or limits).")
        else:
            print(f"  -> Skipping non-actionable decision: {action} {decision['symbol']}")
            
    print(f"\nWorkflow complete. Generated {len(intents)} intents and {len(previews)} previews.")
    print("NO ORDERS WERE SUBMITTED.")

if __name__ == "__main__":
    asyncio.run(run_workflow())
