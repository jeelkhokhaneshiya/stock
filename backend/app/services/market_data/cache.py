from typing import Dict, Any, Optional
from datetime import datetime, timezone

class MarketDataCache:
    def __init__(self):
        # In-memory store: { key: (data, timestamp) }
        self._store: Dict[str, tuple[Any, datetime]] = {}

    def get(self, key: str, max_age_seconds: int) -> Optional[Any]:
        if key not in self._store:
            return None
        
        data, timestamp = self._store[key]
        age = (datetime.now(timezone.utc) - timestamp).total_seconds()
        
        if age > max_age_seconds:
            # Data is too old, remove it
            del self._store[key]
            return None
            
        return data

    def set(self, key: str, data: Any):
        self._store[key] = (data, datetime.now(timezone.utc))

    def clear(self):
        self._store.clear()

# Global cache instance for Phase 3
cache = MarketDataCache()
