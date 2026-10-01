from app.core.config import settings
from app.services.market_data.mock_provider import MockMarketDataProvider
from app.services.market_data.service import MarketDataService

def get_market_data_service() -> MarketDataService:
    provider_name = settings.MARKET_DATA_PROVIDER.lower()
    
    if provider_name == "mock":
        provider = MockMarketDataProvider()
    else:
        # Fallback to mock if an unsupported provider is requested
        provider = MockMarketDataProvider()
        
    return MarketDataService(provider)
