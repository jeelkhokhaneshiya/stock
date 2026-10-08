from typing import Dict, Any, List
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class AlertEngine:
    def __init__(self):
        # In-memory alert store for now, can be moved to DB
        self.alerts = []
        self.last_triggered: Dict[str, datetime] = {}

    def trigger_alert(self, event_type: str, message: str, metadata: Dict[str, Any] = None):
        """
        Foundation for alert events.
        Supported events: BUY_CANDIDATE_FOUND, HOLD_CHANGED, SELL_REVIEW_TRIGGERED, RISK_INCREASED, DATA_STALE, BROKER_DISCONNECTED
        """
        metadata = metadata or {}
        symbol = metadata.get("symbol", "GLOBAL")
        
        # Duplicate alert protection (throttle identical event_type + symbol to once per 24 hours)
        dedup_key = f"{event_type}_{symbol}"
        now = datetime.now(timezone.utc)
        
        if dedup_key in self.last_triggered:
            last_time = self.last_triggered[dedup_key]
            # If triggered within last 24 hours, suppress duplicate
            if (now - last_time).total_seconds() < 86400:
                return

        alert = {
            "id": f"alert_{len(self.alerts) + 1}",
            "event_type": event_type,
            "message": message,
            "metadata": metadata,
            "timestamp": now.isoformat(),
            "read": False
        }
        self.alerts.append(alert)
        self.last_triggered[dedup_key] = now
        logger.warning(f"ALERT [{event_type}]: {message}")
        
    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        return sorted(self.alerts, key=lambda x: x["timestamp"], reverse=True)[:limit]
        
    def check_portfolio_alerts(self, holdings_analysis: List[Dict[str, Any]], buy_candidates: List[Dict[str, Any]]):
        for h in holdings_analysis:
            decision = h.get("analysis", {}).get("decision")
            symbol = h.get("symbol")
            if decision == "SELL_REVIEW":
                self.trigger_alert("SELL_REVIEW_TRIGGERED", f"{symbol} requires SELL review due to deteriorating metrics.", {"symbol": symbol})
            elif decision == "WATCH":
                self.trigger_alert("HOLD_CHANGED", f"{symbol} downgraded to WATCH.", {"symbol": symbol})
                
            freshness = h.get("analysis", {}).get("data_freshness")
            if freshness == "STALE":
                self.trigger_alert("DATA_STALE", f"Market data for {symbol} is stale.", {"symbol": symbol})
                
        for c in buy_candidates:
            if c.get("decision") == "BUY_CANDIDATE":
                self.trigger_alert("BUY_CANDIDATE_FOUND", f"New BUY candidate found: {c.get('symbol')}", {"symbol": c.get("symbol"), "score": c.get("overall_score")})

# Global instance for mock DB
_global_alert_engine = AlertEngine()

def get_alert_engine():
    return _global_alert_engine
