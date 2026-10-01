from app.core.config import settings

class SafetyStatus:
    SAFE = "SAFE"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"

class SafetyMonitor:
    def check_safety(self, portfolio_id: str, decision: dict = None) -> dict:
        status = SafetyStatus.SAFE
        reasons = []

        if settings.BROKER_EXECUTION_BLOCKED:
            if settings.EXECUTION_MODE == "LIVE":
                return {"status": SafetyStatus.BLOCKED, "reasons": ["LIVE_EXECUTION_BLOCKED"]}

        if settings.EXECUTION_MODE == "LIVE" and not settings.LIVE_EXECUTION_UNLOCKED:
            return {"status": SafetyStatus.BLOCKED, "reasons": ["LIVE_EXECUTION_NOT_UNLOCKED"]}

        if settings.ENABLE_LIVE_TRADING:
            if not settings.LIVE_EXECUTION_UNLOCKED:
                return {"status": SafetyStatus.BLOCKED, "reasons": ["LIVE_EXECUTION_NOT_UNLOCKED"]}

        if settings.AUTONOMOUS_KILL_SWITCH:
            return {"status": SafetyStatus.BLOCKED, "reasons": ["AUTONOMOUS_KILL_SWITCH_ACTIVE"]}
            
        # Additional checks can be added here
        return {"status": status, "reasons": reasons}
