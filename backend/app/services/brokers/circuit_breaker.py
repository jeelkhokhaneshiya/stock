from datetime import datetime, timezone

class CircuitState:
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, cooldown_seconds: int = 60):
        self.state = CircuitState.CLOSED
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.failure_count = 0
        self.last_failure_time = None
        
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            
    def record_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        
    def is_allowed(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if self.last_failure_time:
                elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
                if elapsed > self.cooldown_seconds:
                    self.state = CircuitState.HALF_OPEN
                    return True
            return False
        if self.state == CircuitState.HALF_OPEN:
            return True
        return False
