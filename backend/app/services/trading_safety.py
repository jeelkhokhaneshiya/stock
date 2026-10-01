from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class TradingSafety:
    @staticmethod
    def ensure_safe_mode():
        if settings.TRADING_MODE != "paper" or not settings.ENABLE_LIVE_TRADING:
            logger.warning("Attempted to execute live trade but ENABLE_LIVE_TRADING is false.")
            raise Exception("Live trading is currently disabled.")
