import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class LiveBrokerExecutionGuard:
    @staticmethod
    def verify_execution_allowed():
        """
        Guards against real order execution.
        Raises ValueError if LIVE_TRADING is disabled.
        For Phase 9.1, it must ALWAYS reject live execution.
        """
        if not settings.ENABLE_LIVE_TRADING:
            logger.warning("Live execution blocked: LIVE_TRADING_DISABLED")
            raise ValueError("LIVE_TRADING_DISABLED")
        
        # Even if ENABLE_LIVE_TRADING is true, for Phase 9.1 we should reject
        # but the prompt says: "The guard must reject any future live execution request when: ENABLE_LIVE_TRADING != true. For Phase 9.1 it must ALWAYS reject live execution."
        # This means if someone maliciously bypassed ENABLE_LIVE_TRADING=false, we still block it.
        # But wait, if they enable it, should we hardcode a block? The requirement says:
        # "For Phase 9.1 it must ALWAYS reject live execution."
        
        # Let's enforce it strictly:
        logger.error("Live execution blocked: Phase 9.1 does not support live execution.")
        raise ValueError("LIVE_TRADING_DISABLED")
