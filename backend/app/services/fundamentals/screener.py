import httpx
from bs4 import BeautifulSoup
import re
import logging
from typing import Optional, Dict

from app.services.fundamentals.base import FundamentalDataProvider, FundamentalResult, FundamentalProviderStatus

logger = logging.getLogger(__name__)

class ScreenerFundamentalDataProvider(FundamentalDataProvider):
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def _parse_float(self, val: Optional[str]) -> Optional[float]:
        if not val:
            return None
        # Remove commas and % signs
        clean_val = val.replace(',', '').replace('%', '').strip()
        try:
            return float(clean_val)
        except ValueError:
            return None

    def get_fundamentals(self, symbol: str, exchange: str, isin: str = "") -> FundamentalResult:
        # Screener typically uses the base NSE symbol
        screener_symbol = symbol.replace('-EQ', '').strip()
        
        urls_to_try = [
            f"https://www.screener.in/company/{screener_symbol}/consolidated/",
            f"https://www.screener.in/company/{screener_symbol}/"
        ]
        
        resp = None
        for url in urls_to_try:
            try:
                resp = httpx.get(url, headers=self.headers, timeout=10.0)
                if resp.status_code == 200:
                    break
            except Exception as e:
                logger.error(f"Screener request failed for {url}: {e}")
                
        if not resp or resp.status_code != 200:
            return FundamentalResult(
                status=FundamentalProviderStatus.NOT_FOUND,
                provider="SCREENER",
                symbol=symbol,
                error_message=f"Could not fetch data for {screener_symbol}"
            )
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Name
        company_name = screener_symbol
        name_h1 = soup.find('h1', class_='margin-0')
        if name_h1:
            company_name = name_h1.text.strip()
            
        data = {}
        
        # Top ratios
        top_ratios = soup.find('ul', id='top-ratios')
        if top_ratios:
            for li in top_ratios.find_all('li'):
                name_span = li.find('span', class_='name')
                val_span = li.find('span', class_='number')
                if name_span and val_span:
                    data[name_span.text.strip()] = val_span.text.strip()

        def get_row_data(section_id, row_name):
            section = soup.find('section', id=section_id)
            if not section: return None
            for tr in section.find_all('tr'):
                tds = tr.find_all('td')
                if not tds: continue
                name = tds[0].text.strip()
                if row_name.lower() in name.lower():
                    # Get the last column (TTM or latest year)
                    return tds[-1].text.strip()
            return None

        # Data extraction
        # Revenue is in 'profit-loss' section under 'Sales'
        revenue_str = get_row_data('profit-loss', 'Sales')
        net_profit_str = get_row_data('profit-loss', 'Net Profit')
        eps_str = get_row_data('profit-loss', 'EPS')
        cash_flow_str = get_row_data('cash-flow', 'Net Cash Flow')
        promoter_str = get_row_data('shareholding', 'Promoters')
        fii_str = get_row_data('shareholding', 'FIIs')
        dii_str = get_row_data('shareholding', 'DIIs')
        public_str = get_row_data('shareholding', 'Public')
        
        pe_str = data.get('Stock P/E')
        roe_str = data.get('ROE')
        roce_str = data.get('ROCE')
        debt_equity_str = data.get('Debt to equity')
        book_value_str = data.get('Book Value')
        market_cap_str = data.get('Market Cap')
        div_yield_str = data.get('Dividend Yield')
        
        # Parse fields
        promoter = self._parse_float(promoter_str)
        fii = self._parse_float(fii_str)
        dii = self._parse_float(dii_str)
        public = self._parse_float(public_str)
        
        inst_holding = 0.0
        if fii is not None: inst_holding += fii
        if dii is not None: inst_holding += dii
        
        return FundamentalResult(
            status=FundamentalProviderStatus.AVAILABLE,
            provider="SCREENER",
            symbol=symbol,
            provider_ticker=screener_symbol,
            company_name=company_name,
            identity_verified=True,
            
            revenue=self._parse_float(revenue_str),
            net_profit=self._parse_float(net_profit_str),
            eps=self._parse_float(eps_str),
            free_cash_flow=self._parse_float(cash_flow_str),
            
            pe_ratio=self._parse_float(pe_str),
            roe=self._parse_float(roe_str),
            roce=self._parse_float(roce_str),
            debt_to_equity=self._parse_float(debt_equity_str),
            book_value=self._parse_float(book_value_str),
            market_cap=self._parse_float(market_cap_str),
            dividend_yield=self._parse_float(div_yield_str),
            
            promoter_holding=promoter,
            institutional_holding=inst_holding if (fii is not None or dii is not None) else None,
            public_holding=public
        )
