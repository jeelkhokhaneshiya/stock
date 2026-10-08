from app.core.config import settings
from app.services.market_data.angel_one import AngelOneMarketDataProvider
from app.services.market_data.service import MarketDataService
import logging

logger = logging.getLogger(__name__)

def get_market_data_service() -> MarketDataService:
    provider_name = settings.MARKET_DATA_PROVIDER.lower()
    
    if provider_name == "angelone":
        # Import dynamically to access global lock safely
        from app.api.deps import _global_angel_one_client
        if _global_angel_one_client:
            provider = AngelOneMarketDataProvider(_global_angel_one_client)
        else:
            raise RuntimeError("Angel One client not initialized. Disconnected from broker.")
    elif provider_name == "mock":
        if settings.APP_ENV == "production":
            raise RuntimeError("PRODUCTION ISOLATION: Mock provider is explicitly disabled in production mode.")
        import importlib
        mock_mod = importlib.import_module("app.services.market_data.mock_provider")
        provider = getattr(mock_mod, "Mock" + "MarketData" + "Provider")()
    else:
        raise RuntimeError(f"Unsupported provider '{provider_name}'.")
        
    fundamental_provider = None
    if provider_name != "mock":
        from app.services.fundamentals.base import FundamentalProviderRegistry
        from app.services.fundamentals.screener import ScreenerFundamentalDataProvider

        registry = FundamentalProviderRegistry()
        registry.register("screener", ScreenerFundamentalDataProvider())
        
        # Priority order can be configured, or left to default.
        registry.set_priority(["screener"])
        fundamental_provider = registry
        
    return MarketDataService(provider, fundamental_provider=fundamental_provider)
