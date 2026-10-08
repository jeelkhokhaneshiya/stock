import logging
from typing import List, Any, Dict
from datetime import datetime, timezone
import threading
from app.services.interfaces import MarketDataProvider
from app.services.brokers.angel_one.client import AngelOneClient
from app.schemas.market_data import HistoricalBar
from app.services.market_session import MarketSessionService
from app.services.discovery.scanner import MarketScanner

logger = logging.getLogger(__name__)

class AngelOneMarketDataProvider(MarketDataProvider):
    """
    Real Angel One Market Data Engine.
    Uses the global AngelOneClient session.
    """
    _master_mapping: Dict[str, str] = {}
    _mapping_lock = threading.Lock()

    def __init__(self, client: AngelOneClient):
        self.client = client
        self.market_session = MarketSessionService()
        self._ensure_mapping()

    def _ensure_mapping(self):
        with self._mapping_lock:
            if not self._master_mapping:
                scanner = MarketScanner()
                master_list = scanner.fetch_master_universe()
                for item in master_list:
                    symbol = item.get("symbol")
                    exch = item.get("exch_seg")
                    token = item.get("token")
                    inst_type = item.get("instrumenttype", "")
                    
                    if symbol and exch and token:
                        # For NSE, strictly map only standard equities (-EQ) to avoid derivatives/ambiguity
                        if exch == "NSE":
                            if symbol.endswith("-EQ") and inst_type == "":
                                std_symbol = symbol[:-3]  # Remove exactly "-EQ" at the end
                                key = f"{exch}:{std_symbol}"
                                self._master_mapping[key] = token
                        else:
                            # For BSE or others, just use the symbol
                            key = f"{exch}:{symbol}"
                            # Prevent overwriting if already exists (prefer first match if ambiguous)
                            if key not in self._master_mapping:
                                self._master_mapping[key] = token
                                
                logger.info(f"Loaded {len(self._master_mapping)} token mappings from Angel One.")

    def _get_token(self, symbol: str, exchange: str) -> str:
        key = f"{exchange}:{symbol}"
        return self._master_mapping.get(key, "")

    def get_quote(self, symbol: str, exchange: str) -> Any:
        if symbol.isdigit():
            token = symbol
        else:
            token = self._get_token(symbol, exchange)
            
        if not token:
            logger.warning(f"Skipping Angel One quote for {symbol} - could not resolve token")
            return None
            
        tradingsymbol = symbol + "-EQ" if exchange == "NSE" else symbol
        
        try:
            data = self.client.get_ltp_data(exchange, tradingsymbol, token)
        except Exception as e:
            logger.error(f"Failed to fetch quote for {symbol}: {e}")
            return None
            
        if not data:
            return None
            
        try:
            ltp = float(data.get("ltp", 0))
        except (ValueError, TypeError):
            ltp = 0.0
            
        if ltp <= 0:
            return None
            
        try:
            o = float(data.get("open", 0))
            h = float(data.get("high", 0))
            l = float(data.get("low", 0))
            c = float(data.get("close", 0))
        except (ValueError, TypeError):
            o = h = l = c = 0.0
            
        if h > 0 and l > 0 and h < l:
            logger.warning(f"Invalid High/Low in Angel One quote for {symbol}")
            return None
            
        from app.schemas.market_data import MarketQuote
        
        return MarketQuote(
            symbol=symbol,
            exchange=exchange,
            price=ltp,
            open=o if o > 0 else None,
            high=h if h > 0 else None,
            low=l if l > 0 else None,
            previous_close=c if c > 0 else None,
            volume=None,
            currency="INR",
            data_source="ANGEL_ONE",
            timestamp=datetime.now(timezone.utc),
            is_stale=False
        )

    def get_historical_data(self, symbol: str, exchange: str, timeframe: str, start_date: datetime, end_date: datetime) -> List[HistoricalBar]:
        """
        Fetches real OHLC from Angel One.
        Timeframes: ONE_MINUTE, THREE_MINUTE, FIVE_MINUTE, TEN_MINUTE, FIFTEEN_MINUTE, THIRTY_MINUTE, ONE_HOUR, ONE_DAY
        """
        if symbol.isdigit():
            token = symbol
        else:
            token = self._get_token(symbol, exchange)
            
        if not token:
            logger.warning(f"Skipping Angel One historical data for {symbol} - could not resolve token")
            return []
            
        payload = {
            "exchange": exchange,
            "symboltoken": token,
            "interval": timeframe,
            "fromdate": start_date.strftime("%Y-%m-%d %H:%M"),
            "todate": end_date.strftime("%Y-%m-%d %H:%M")
        }
        
        try:
            res = self.client.get_candle_data(payload)
        except Exception as e:
            logger.error("Failed to fetch historical data from Angel One: %s", str(e))
            raise ValueError(f"Failed to fetch historical data: {str(e)}")
            
        data = res if isinstance(res, list) else []
        if not data:
            return []

        bars = []
        for row in data:
            try:
                dt = datetime.fromisoformat(row[0]).astimezone(timezone.utc)
                o, h, l, c, v = float(row[1]), float(row[2]), float(row[3]), float(row[4]), int(row[5])
                
                if h < max(o, c) or l > min(o, c) or v < 0:
                    continue
                    
                bar = HistoricalBar(
                    symbol=symbol,
                    exchange=exchange,
                    data_source="ANGEL_ONE",
                    timestamp=dt,
                    open=o,
                    high=h,
                    low=l,
                    close=c,
                    volume=v
                )
                bars.append(bar)
            except Exception as e:
                logger.warning(f"Failed to parse candle {row}: {e}")
                
        if bars and timeframe in ["ONE_MINUTE", "THREE_MINUTE", "FIVE_MINUTE", "TEN_MINUTE", "FIFTEEN_MINUTE"]:
            age = (datetime.now(timezone.utc) - bars[-1].timestamp).total_seconds()
            if self.market_session.get_market_status() == "OPEN" and age > 1800:
                logger.warning(f"Data for {symbol} is stale. Age: {age}s")
                for bar in bars:
                    bar.is_stale = True

        return bars

    def get_company_info(self, symbol: str, exchange: str) -> Any:
        # Angel One does not officially provide fundamental company info.
        return None

    def get_fundamentals(self, symbol: str, exchange: str, isin: str = None) -> Any:
        # Angel One does not officially provide fundamental data.
        return None

    def get_etf_info(self, symbol: str, exchange: str) -> Any:
        return None

    def get_mutual_fund_info(self, identifier: str) -> Any:
        return None
