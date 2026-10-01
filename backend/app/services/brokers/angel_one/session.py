from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class SessionState:
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    EXPIRED = "EXPIRED"
    RECONNECTING = "RECONNECTING"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"

class AngelOneSessionManager:
    def __init__(self):
        self.state = SessionState.DISCONNECTED
        self.last_success_at = None
        self.last_failure_at = None
        self.failure_count = 0
        
    def login(self):
        if self.state in [SessionState.CONNECTED, SessionState.BLOCKED]:
            return
        
        self.state = SessionState.CONNECTING
        try:
            # Simulated safe authentication check
            self.state = SessionState.CONNECTED
            self.last_success_at = datetime.now(timezone.utc)
            self.failure_count = 0
        except Exception as e:
            self.state = SessionState.FAILED
            self.last_failure_at = datetime.now(timezone.utc)
            self.failure_count += 1
            # Never log secrets
            logger.error("Authentication failed safely")

    def get_status(self):
        return {
            "state": self.state,
            "last_success_at": self.last_success_at.isoformat() if self.last_success_at else None,
            "last_failure_at": self.last_failure_at.isoformat() if self.last_failure_at else None,
            "failure_count": self.failure_count
        }
