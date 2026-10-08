import os
import sys
import time
import json
import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.services.brokers.angel_one.auth import AngelOneAuth
from app.services.brokers.angel_one.client import AngelOneClient
from app.services.brokers.angel_one.data_service import AngelOneDataService
from app.services.portfolio.portfolio_manager import PortfolioManager
import app.api.deps

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Worker")

AUDIT_LOG_FILE = "decisions_audit.jsonl"
CYCLE_DELAY_SECONDS = 300 # 5 minutes

def run_worker(once: bool = False):
    logger.info("Starting Autonomous Investment Decision Worker (DRY-RUN)")
    
    # 14. Keep all existing real-money execution guards enabled.
    os.environ["ENABLE_LIVE_TRADING"] = "false"
    os.environ["LIVE_EXECUTION_UNLOCKED"] = "false"
    os.environ["BROKER_EXECUTION_BLOCKED"] = "true"
    os.environ["MARKET_DATA_PROVIDER"] = "angelone"
    settings.MARKET_DATA_PROVIDER = "angelone"

    # Authenticate once
    auth = AngelOneAuth(
        client_id=settings.ANGEL_ONE_CLIENT_ID,
        password=settings.ANGEL_ONE_PASSWORD,
        api_key=settings.ANGEL_ONE_API_KEY,
        totp_secret=settings.ANGEL_ONE_TOTP_SECRET
    )
    client = AngelOneClient(auth=auth)
    
    try:
        if not (settings.ANGEL_ONE_CLIENT_ID and settings.ANGEL_ONE_PASSWORD and settings.ANGEL_ONE_API_KEY and settings.ANGEL_ONE_TOTP_SECRET):
            logger.warning("Missing Angel One credentials. Dry-run aborting.")
            if once: return
            sys.exit(1)
            
        client.authenticate()
        logger.info("Successfully authenticated with Angel One.")
    except Exception as e:
        logger.error(f"Initial authentication failed: {e}")
        if once: return
        sys.exit(1)
        
    app.api.deps._global_angel_one_client = client
    data_svc = AngelOneDataService(client)
    manager = PortfolioManager(client=data_svc)
    
    # Initialize ExecutionReadinessLayer (Phase 7)
    from app.services.execution.readiness import ExecutionReadinessLayer, ExecutionReadinessError
    readiness_layer = ExecutionReadinessLayer(manager, audit_log_path="order_intent_audit.jsonl")
    
    while True:
        logger.info("Starting analysis cycle...")
        try:
            analysis = manager.get_full_portfolio_analysis()
            
            if analysis.get("status") == "OK":
                action_plan = analysis.get("daily_investment_action_plan", [])
                logger.info(f"Cycle completed. Generated {len(action_plan)} decisions.")
                
                # 13. Produce a clear machine-readable decision record for every cycle.
                with open(AUDIT_LOG_FILE, "a") as f:
                    for decision in action_plan:
                        action = decision.get("action", "NO_ACTION")
                        execution_status = "NOT_APPLICABLE"
                        safety_status = "SAFE"
                        rejection_reason = ""
                        
                        if action in ["BUY", "BUY_MORE", "REDUCE", "SELL"]:
                            try:
                                intent = readiness_layer.generate_intent(decision)
                                execution_status = "INTENT_GENERATED"
                                logger.info(f"Intent generated for {decision.get('symbol')} ({action})")
                            except ExecutionReadinessError as ere:
                                execution_status = "BLOCKED"
                                rejection_reason = str(ere)
                                logger.warning(f"Intent blocked for {decision.get('symbol')}: {rejection_reason}")
                            except Exception as ex:
                                execution_status = "ERROR"
                                rejection_reason = f"Internal Error: {str(ex)}"
                                logger.error(f"Error generating intent for {decision.get('symbol')}: {rejection_reason}")
                                
                        record = {
                            "cycle_id": analysis.get("generated_at"),
                            "symbol": decision.get("symbol", "UNKNOWN"),
                            "decision": action,
                            "quantity": decision.get("quantity", 0),
                            "current_price": decision.get("current_price", 0.0),
                            "estimated_value": decision.get("estimated_value", 0.0),
                            "confidence": decision.get("confidence", 0.0),
                            "decision_reason": "; ".join(decision.get("reasons", [])),
                            "risks": decision.get("risks", []),
                            "data_source": "ANGEL_ONE",
                            "data_freshness": decision.get("data_freshness", "UNKNOWN"),
                            "execution_readiness_status": execution_status,
                            "rejection_reason": rejection_reason,
                            "safety_status": safety_status,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        f.write(json.dumps(record) + "\n")
            else:
                logger.warning(f"Analysis cycle skipped or failed: {analysis.get('reason')}")
                
        except Exception as e:
            # 11. The worker must survive temporary network/API failures without using mock data.
            logger.error(f"Cycle error: {e}. Worker will survive and retry next cycle.")
            
        if once:
            break
            
        logger.info(f"Waiting for {CYCLE_DELAY_SECONDS} seconds before next cycle...")
        time.sleep(CYCLE_DELAY_SECONDS)

if __name__ == "__main__":
    run_worker()
