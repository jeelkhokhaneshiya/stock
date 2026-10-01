import logging
from datetime import datetime, timezone
from typing import List, Any
from app.services.interfaces import MarketDataProvider
from app.schemas.market_data import (
    MarketQuote, HistoricalBar, CompanyInfo, 
    FundamentalData, ETFInfo, MutualFundInfo
)
from app.services.market_data.cache import cache
from app.core.config import settings

logger = logging.getLogger(__name__)

class MarketDataService:
    def __init__(self, provider: MarketDataProvider):
        self.provider = provider
        
    def _check_stale(self, data: Any, max_age: int) -> Any:
        if hasattr(data, 'timestamp') and data.timestamp:
            age = (datetime.now(timezone.utc) - data.timestamp).total_seconds()
            if age > max_age:
                data.is_stale = True
        return data

    def get_quote(self, symbol: str, exchange: str = "NSE") -> MarketQuote:
        cache_key = f"quote:{exchange}:{symbol}"
        cached_data = cache.get(cache_key, settings.QUOTE_MAX_AGE_SECONDS)
        
        if cached_data:
            return cached_data
            
        try:
            # Here we might implement timeout/retry logic for real providers
            data = self.provider.get_quote(symbol, exchange)
            data = self._check_stale(data, settings.QUOTE_MAX_AGE_SECONDS)
            cache.set(cache_key, data)
            return data
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            raise ValueError(f"Failed to fetch market data: {str(e)}")

    def get_historical_data(self, symbol: str, exchange: str, timeframe: str, start_date: datetime, end_date: datetime) -> List[HistoricalBar]:
        cache_key = f"hist:{exchange}:{symbol}:{timeframe}:{start_date.isoformat()}:{end_date.isoformat()}"
        cached_data = cache.get(cache_key, settings.HISTORICAL_DATA_MAX_AGE)
        
        if cached_data:
            return cached_data
            
        try:
            data = self.provider.get_historical_data(symbol, exchange, timeframe, start_date, end_date)
            # Not marking individual bars as stale here, as historical data is generally static
            cache.set(cache_key, data)
            return data
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            raise ValueError(f"Failed to fetch historical data: {str(e)}")

    def get_company_info(self, symbol: str, exchange: str = "NSE") -> CompanyInfo:
        cache_key = f"company:{exchange}:{symbol}"
        cached_data = cache.get(cache_key, settings.HISTORICAL_DATA_MAX_AGE)
        
        if cached_data:
            return cached_data
            
        try:
            data = self.provider.get_company_info(symbol, exchange)
            data = self._check_stale(data, settings.HISTORICAL_DATA_MAX_AGE)
            cache.set(cache_key, data)
            return data
        except Exception as e:
            raise ValueError(f"Failed to fetch company info: {str(e)}")

    def get_fundamentals(self, symbol: str, exchange: str = "NSE") -> FundamentalData:
        cache_key = f"fund:{exchange}:{symbol}"
        cached_data = cache.get(cache_key, settings.HISTORICAL_DATA_MAX_AGE)
        
        if cached_data:
            return cached_data
            
        try:
            data = self.provider.get_fundamentals(symbol, exchange)
            data = self._check_stale(data, settings.HISTORICAL_DATA_MAX_AGE)
            cache.set(cache_key, data)
            return data
        except Exception as e:
            raise ValueError(f"Failed to fetch fundamentals: {str(e)}")

    def get_etf_info(self, symbol: str, exchange: str = "NSE") -> ETFInfo:
        try:
            data = self.provider.get_etf_info(symbol, exchange)
            return self._check_stale(data, settings.HISTORICAL_DATA_MAX_AGE)
        except Exception as e:
            raise ValueError(f"Failed to fetch ETF info: {str(e)}")

    def get_mutual_fund_info(self, identifier: str) -> MutualFundInfo:
        try:
            data = self.provider.get_mutual_fund_info(identifier)
            return self._check_stale(data, settings.HISTORICAL_DATA_MAX_AGE)
        except Exception as e:
            raise ValueError(f"Failed to fetch Mutual Fund info: {str(e)}")
