from datetime import datetime, timezone

class BrokerHealthStatus:
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    RATE_LIMITED = "RATE_LIMITED"
    STALE_DATA = "STALE_DATA"
    BLOCKED = "BLOCKED"

class BrokerHealthService:
    def __init__(self):
        self.status = BrokerHealthStatus.HEALTHY
        self.latency_ms = 0
        self.consecutive_failures = 0
        self.last_success_at = datetime.now(timezone.utc)
        self.last_failure_at = None
        self.rate_limited = False
        self.authentication_valid = True
        self.data_available = True
        
    def record_success(self, latency_ms: int):
        self.consecutive_failures = 0
        self.latency_ms = latency_ms
        self.last_success_at = datetime.now(timezone.utc)
        self.rate_limited = False
        self.status = BrokerHealthStatus.HEALTHY
        
    def record_failure(self, error_type: str):
        self.consecutive_failures += 1
        self.last_failure_at = datetime.now(timezone.utc)
        
        if error_type == "AUTH":
            self.authentication_valid = False
            self.status = BrokerHealthStatus.AUTHENTICATION_REQUIRED
        elif error_type == "RATE_LIMIT":
            self.rate_limited = True
            self.status = BrokerHealthStatus.RATE_LIMITED
        elif self.consecutive_failures > 3:
            self.status = BrokerHealthStatus.UNAVAILABLE

    def get_status(self):
        return {
            "status": self.status,
            "latency_ms": self.latency_ms,
            "last_success_at": self.last_success_at.isoformat() if self.last_success_at else None,
            "last_failure_at": self.last_failure_at.isoformat() if self.last_failure_at else None,
            "consecutive_failures": self.consecutive_failures,
            "rate_limited": self.rate_limited,
            "authentication_valid": self.authentication_valid,
            "data_available": self.data_available
        }
