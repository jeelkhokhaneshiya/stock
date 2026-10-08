import asyncio
import json
import logging
import os
import signal
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.core.config import settings
from app.services.brokers.angel_one.auth import AngelOneAuth
from app.services.brokers.angel_one.client import AngelOneClient
from app.services.brokers.angel_one.data_service import AngelOneDataService
from app.services.portfolio.portfolio_manager import PortfolioManager
from app.services.notification_service import get_notification_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATE_FILE = "monitoring_state.json"
HEALTH_FILE = "monitoring_health.json"

class MonitoringWorker:
    def __init__(self, interval_seconds: int = 3600):
        self.interval_seconds = interval_seconds
        self.notification_service = get_notification_service()
        self.client = None
        self.pm = None
        self.running = False
        
        self.health = {
            "last_successful_cycle": None,
            "last_successful_auth": None,
            "last_successful_portfolio": None,
            "last_successful_market_data": None,
            "last_successful_notification": None,
            "consecutive_failures": 0,
            "last_error_timestamp": None,
            "status": "STARTING"
        }
        self._load_state()

    def _load_state(self):
        self.state = {}
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    self.state = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load state: {e}")

    def _save_state(self):
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.state, f)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            
    def _save_health(self):
        try:
            with open(HEALTH_FILE, "w", encoding="utf-8") as f:
                json.dump(self.health, f)
        except Exception as e:
            logger.error(f"Failed to save health state: {e}")
            
    def _update_health(self, key: str, value=None):
        if value is None:
            value = datetime.now(timezone.utc).isoformat()
        self.health[key] = value
        self._save_health()

    def _authenticate(self) -> bool:
        try:
            auth = AngelOneAuth(
                api_key=settings.ANGEL_ONE_API_KEY,
                client_id=settings.ANGEL_ONE_CLIENT_ID,
                password=settings.ANGEL_ONE_PASSWORD,
                totp_secret=settings.ANGEL_ONE_TOTP_SECRET,
            )
            self.client = AngelOneClient(auth=auth)
            self.client.authenticate()
            data_svc = AngelOneDataService(self.client)
            self.pm = PortfolioManager(client=data_svc)
            
            self._update_health("last_successful_auth")
            return True
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            self._update_health("last_error_timestamp")
            self.notification_service.send_notification(f"⚠️ *ALERT:* Angel One Authentication failed.\nError: {e}")
            return False

    def _format_notification(self, decision: Dict[str, Any]) -> str:
        symbol = decision.get("symbol")
        action = decision.get("action")
        price = decision.get("current_price", 0)
        qty = decision.get("quantity", 0)
        est = decision.get("estimated_value", 0)
        reasons = "\n- " + "\n- ".join(decision.get("reasons", []))
        risks = "\n- " + "\n- ".join(decision.get("risks", [])) if decision.get("risks") else "None"
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        msg = f"📈 *INVESTMENT ALERT: {symbol}*\n\n"
        msg += f"*Action:* {action}\n"
        msg += f"*Price:* ₹{price}\n"
        
        if qty > 0:
            msg += f"*Suggested Qty:* {qty}\n"
            msg += f"*Estimated Value:* ₹{est}\n"
            
        msg += f"\n*Reasoning:*{reasons}\n"
        if risks != "None":
            msg += f"\n*Risks:*{risks}\n"
            
        msg += f"\n_Time: {ts}_\n"
        msg += "⚠️ _This is a notification only. Real orders require explicit human confirmation._"
        return msg

    def _process_decisions(self, action_plan: List[Dict[str, Any]]):
        for decision in action_plan:
            symbol = decision.get("symbol")
            action = decision.get("action")
            
            # We care about actionable changes: BUY, BUY_MORE, SELL, REDUCE
            # or if a previous BUY becomes HOLD/WATCH/NO_ACTION
            
            prev_state = self.state.get(symbol, {})
            prev_action = prev_state.get("action")
            
            # Meaningful change logic:
            should_notify = False
            if action in ["BUY", "BUY_MORE", "SELL", "REDUCE"]:
                if action != prev_action:
                    should_notify = True
                elif decision.get("quantity", 0) != prev_state.get("quantity", 0) and abs(decision.get("quantity", 0) - prev_state.get("quantity", 0)) > 5:
                    should_notify = True # Meaningful quantity change
            elif prev_action in ["BUY", "BUY_MORE", "SELL", "REDUCE"] and action in ["HOLD", "WATCH", "NO_ACTION"]:
                should_notify = True # Opportunity invalidated
                
            if should_notify:
                msg = self._format_notification(decision)
                success = self.notification_service.send_notification(msg)
                if success:
                    self._update_health("last_successful_notification")
                    # Save state only if notification succeeded
                    self.state[symbol] = {
                        "action": action,
                        "quantity": decision.get("quantity", 0),
                        "price": decision.get("current_price", 0),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    self._save_state()

    def run_cycle(self):
        logger.info("Starting monitoring cycle...")
        self._update_health("status", "RUNNING")
        
        if not self.client or not self.client.auth.is_authenticated():
            if not self._authenticate():
                self.health["consecutive_failures"] += 1
                self._update_health("status", "AUTH_FAILED")
                return

        try:
            analysis = self.pm.get_full_portfolio_analysis()
            if analysis["status"] != "OK":
                self.health["consecutive_failures"] += 1
                logger.error(f"Portfolio analysis failed: {analysis.get('reason')}")
                if "disconnected" in analysis.get('reason', '').lower() or "timeout" in analysis.get('reason', '').lower():
                    self.notification_service.send_notification(f"⚠️ *ALERT:* Broker connection issue.\nReason: {analysis.get('reason')}")
                self._update_health("last_error_timestamp")
                self._update_health("status", "DATA_FAILED")
                return
                
            self._update_health("last_successful_portfolio")
            self._update_health("last_successful_market_data")
            
            action_plan = analysis.get("daily_investment_action_plan", [])
            self._process_decisions(action_plan)
            
            logger.info("Cycle completed successfully.")
            self.health["consecutive_failures"] = 0
            self._update_health("last_successful_cycle")
            self._update_health("status", "HEALTHY")
            
        except Exception as e:
            self.health["consecutive_failures"] += 1
            self._update_health("last_error_timestamp")
            self._update_health("status", "ERROR")
            logger.error(f"Error during cycle: {e}")
            self.notification_service.send_notification(f"⚠️ *ALERT:* Unexpected error in monitoring worker.\nError: {e}")
            
    def stop(self):
        logger.info("Shutting down monitoring service...")
        self.running = False
        self._update_health("status", "STOPPED")

    async def start(self):
        logger.info(f"Starting 24/7 Monitoring Service (Interval: {self.interval_seconds}s)")
        self.running = True
        
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self.stop)
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                pass

        while self.running:
            try:
                self.run_cycle()
            except Exception as e:
                logger.error(f"Fatal cycle error: {e}")
            
            if not self.running:
                break
                
            logger.info(f"Sleeping for {self.interval_seconds} seconds...")
            # Sleep in chunks to allow responsive shutdown
            for _ in range(self.interval_seconds):
                if not self.running:
                    break
                await asyncio.sleep(1)

if __name__ == "__main__":
    interval = int(os.environ.get("MONITORING_INTERVAL_SECONDS", 3600))
    worker = MonitoringWorker(interval_seconds=interval)
    try:
        asyncio.run(worker.start())
    except KeyboardInterrupt:
        worker.stop()
        logger.info("Monitoring service stopped by user.")
