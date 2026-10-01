from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

class MarketSessionService:
    def __init__(self, timezone_str: str = "Asia/Kolkata", start_hour: int = 9, start_minute: int = 15, end_hour: int = 15, end_minute: int = 30):
        self.timezone = ZoneInfo(timezone_str)
        self.start_hour = start_hour
        self.start_minute = start_minute
        self.end_hour = end_hour
        self.end_minute = end_minute
        # For Phase 8 testing, we allow overriding the session state.
        self._override_status = None

    def get_market_status(self) -> str:
        if self._override_status:
            return self._override_status

        now = datetime.now(self.timezone)
        # Weekends are closed
        if now.weekday() >= 5:
            return "MARKET_CLOSED"
            
        current_minutes = now.hour * 60 + now.minute
        start_minutes = self.start_hour * 60 + self.start_minute
        end_minutes = self.end_hour * 60 + self.end_minute
        
        if start_minutes <= current_minutes <= end_minutes:
            return "MARKET_OPEN"
        return "MARKET_CLOSED"

    def set_override(self, status: str):
        """Used for deterministic testing."""
        self._override_status = status
