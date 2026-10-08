from datetime import datetime, timedelta, timezone
from typing import List, Any, Optional
from app.services.interfaces import MarketDataProvider
from app.schemas.market_data import MarketQuote, HistoricalBar, CompanyInfo, FundamentalData, ETFInfo, MutualFundInfo

class MockMarketDataProvider(MarketDataProvider):
    def get_quote(self, symbol: str, exchange: str) -> MarketQuote:
        if symbol.startswith("INVALID"):
            raise ValueError(f"Invalid symbol: {symbol}")
        
        # Deterministic generation
        base_price = sum(ord(c) for c in symbol) * 1.5
        
        return MarketQuote(
            symbol=symbol,
            exchange=exchange,
            price=base_price,
            open=base_price * 0.99,
            high=base_price * 1.05,
            low=base_price * 0.95,
            previous_close=base_price * 0.98,
            volume=10000 + int(base_price),
            currency="INR",
            data_source="mock",
            timestamp=datetime.now(timezone.utc)
        )

    def get_historical_data(self, symbol: str, exchange: str, timeframe: str, start_date: datetime, end_date: datetime) -> List[HistoricalBar]:
        if symbol.startswith("INVALID"):
            raise ValueError(f"Invalid symbol: {symbol}")
            
        seed = sum(ord(c) for c in symbol)
        base_price = seed * 1.5
        bars = []
        
        current = start_date
        trend_increment = 0.0
        while current <= end_date:
            trend_increment += (seed % 5) * 0.1  # Unique trend per symbol
            # Incorporate seed into daily volatility
            daily_factor = 1.0 + (((current.day + seed) % 15) - 7) / 100.0  # -7% to +7%
            price = base_price * daily_factor + trend_increment
            
            bars.append(HistoricalBar(
                symbol=symbol,
                exchange=exchange,
                timestamp=current,
                open=price * 0.99,
                high=price * 1.05,
                low=price * 0.95,
                close=price,
                volume=10000 + int(price),
                adjusted_close=price,
                data_source="mock"
            ))
            current += timedelta(days=1)
            
        return bars

    def get_company_info(self, symbol: str, exchange: str) -> CompanyInfo:
        return CompanyInfo(
            symbol=symbol,
            exchange=exchange,
            name=f"{symbol} Mock Corporation",
            sector="Technology",
            industry="Software",
            country="India",
            currency="INR",
            market_cap=1000000000.0,
            data_source="mock",
            timestamp=datetime.now(timezone.utc)
        )

    def get_fundamentals(self, symbol: str, exchange: str, isin: Optional[str] = None) -> FundamentalData:
        # Generate deterministic but unique values based on symbol string
        seed = sum(ord(c) for c in symbol)
        
        # Introduce simulated missing data for certain symbols to test UNAVAILABLE states
        if seed % 5 == 0:
            return None # Simulate missing fundamentals for 20% of symbols
            
        rev_growth = 0.05 + ((seed % 20) / 100.0) # 0.05 to 0.24
        profit_growth = rev_growth + 0.02
        roe = 0.08 + ((seed % 15) / 100.0)
        debt = 0.1 + ((seed % 30) / 10.0)
        
        return FundamentalData(
            symbol=symbol,
            exchange=exchange,
            revenue=500000000.0 + (seed * 1000000),
            revenue_growth=rev_growth,
            net_income=100000000.0 + (seed * 500000),
            profit_growth=profit_growth,
            eps=10.0 + (seed % 50),
            roe=roe,
            roce=roe + 0.02,
            debt_to_equity=debt,
            operating_margin=0.15 + ((seed % 10) / 100.0),
            net_margin=0.10 + ((seed % 10) / 100.0),
            free_cash_flow=10000000.0 * (seed % 20),
            data_source="mock",
            timestamp=datetime.now(timezone.utc)
        )

    def get_etf_info(self, symbol: str, exchange: str) -> ETFInfo:
        return ETFInfo(
            symbol=symbol,
            exchange=exchange,
            name=f"{symbol} Mock ETF",
            expense_ratio=0.001,
            aum=5000000000.0,
            tracking_index="NIFTY 50",
            volume=500000,
            price=250.0,
            currency="INR",
            data_source="mock",
            timestamp=datetime.now(timezone.utc)
        )

    def get_mutual_fund_info(self, identifier: str) -> MutualFundInfo:
        return MutualFundInfo(
            identifier=identifier,
            name=f"Mock Mutual Fund {identifier}",
            category="Equity - Large Cap",
            nav=55.25,
            nav_date=datetime.now(timezone.utc) - timedelta(days=1),
            expense_ratio=0.005,
            aum=10000000000.0,
            risk_category="High",
            data_source="mock",
            timestamp=datetime.now(timezone.utc)
        )
