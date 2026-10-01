from datetime import datetime, timedelta, timezone
from typing import List, Any
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
            
        base_price = sum(ord(c) for c in symbol) * 1.5
        bars = []
        
        current = start_date
        while current <= end_date:
            daily_factor = 1.0 + ((current.day % 10) - 5) / 100.0  # -5% to +4%
            price = base_price * daily_factor
            
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

    def get_fundamentals(self, symbol: str, exchange: str) -> FundamentalData:
        return FundamentalData(
            symbol=symbol,
            exchange=exchange,
            revenue=500000000.0,
            revenue_growth=0.15,
            net_income=100000000.0,
            profit_growth=0.20,
            eps=15.5,
            roe=0.18,
            roce=0.22,
            debt_to_equity=0.5,
            operating_margin=0.25,
            net_margin=0.20,
            free_cash_flow=120000000.0,
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
