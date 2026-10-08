import os
import httpx
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.services.fundamentals.base import (
    FundamentalResult,
    FundamentalProviderStatus,
    FundamentalDataProvider
)


class FMPFundamentalDataProvider(FundamentalDataProvider):
    """
    Isolated FMP Fundamental Data Provider for validation purposes.
    """

    BASE_URL = "https://financialmodelingprep.com/api/v3"

    def __init__(self, api_key: Optional[str] = None, timeout: float = 15.0):
        self._api_key: Optional[str] = api_key if api_key is not None else settings.FMP_API_KEY
        self._timeout = timeout

    def _http_to_provider_status(self, http_status: int) -> FundamentalProviderStatus:
        if http_status == 200:
            return FundamentalProviderStatus.AVAILABLE
        elif http_status in (401, 403):
            return FundamentalProviderStatus.AUTH_ERROR
        elif http_status == 429:
            return FundamentalProviderStatus.RATE_LIMITED
        elif http_status == 404:
            return FundamentalProviderStatus.NOT_FOUND
        else:
            return FundamentalProviderStatus.PROVIDER_ERROR

    def _get(self, endpoint: str, params: Dict[str, Any] = None) -> tuple[int, Optional[Any]]:
        if not self._api_key:
            logger.warning("FMP_API_KEY is not set.")
            return 401, None

        params = params or {}
        params["apikey"] = self._api_key
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(url, params=params)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if isinstance(data, dict) and "Error Message" in data:
                            logger.error(f"FMP API Error: {data['Error Message']}")
                            if "Invalid API KEY" in data["Error Message"]:
                                return 401, None
                            return 403, None
                        return 200, data
                    except ValueError:
                        return 500, None
                        
                return response.status_code, None
                
        except httpx.TimeoutException:
            logger.error("FMP API request timed out")
            return 408, None
        except Exception as e:
            logger.error(f"FMP API request failed: {str(e)}")
            return 500, None

    def get_fundamentals(self, symbol: str, exchange: str, isin: str = "") -> FundamentalResult:
        """
        Validates ISIN against FMP, fetches statements, and returns FundamentalResult.
        """
        if not self._api_key:
            return FundamentalResult(status=FundamentalProviderStatus.AUTH_ERROR, provider="FMP", error_message="Missing API Key")

        # 1. Identity Validation
        fmp_symbol = None
        company_name = None
        identity_verified = False
        
        if isin:
            status, isin_data = self._get("search-isin", {"isin": isin})
            if status != 200 or not isin_data:
                status, isin_data = self._get("search", {"query": isin})
                
            if status != 200:
                logger.error(f"FMP Identity check failed or returned {status}")
                return FundamentalResult(status=self._http_to_provider_status(status), provider="FMP", http_status=status)
                
            if not isin_data:
                logger.error(f"FMP Identity check returned empty data for ISIN {isin}")
                return FundamentalResult(status=FundamentalProviderStatus.NOT_FOUND, provider="FMP", http_status=404)
                
            if isinstance(isin_data, list) and len(isin_data) > 0:
                fmp_symbol = isin_data[0].get("symbol")
                company_name = isin_data[0].get("name")
                identity_verified = True
            
            if not fmp_symbol:
                logger.error(f"FMP Identity validation failed: ISIN {isin} not found.")
                return FundamentalResult(status=FundamentalProviderStatus.NOT_FOUND, provider="FMP", error_message="ISIN not found")
        else:
            base_symbol = symbol.split('-')[0]
            fmp_symbol = f"{base_symbol}.NS"

        # 2. Fetch Income Statement
        inc_status, inc_data = self._get(f"income-statement/{fmp_symbol}", {"limit": 2})
        if inc_status != 200 or not inc_data or not isinstance(inc_data, list):
            return FundamentalResult(status=self._http_to_provider_status(inc_status), provider="FMP", http_status=inc_status)

        # 3. Fetch Balance Sheet
        bs_status, bs_data = self._get(f"balance-sheet-statement/{fmp_symbol}", {"limit": 1})
        if bs_status != 200 or not bs_data or not isinstance(bs_data, list):
            return FundamentalResult(status=self._http_to_provider_status(bs_status), provider="FMP", http_status=bs_status)

        # 4. Fetch Cash Flow
        cf_status, cf_data = self._get(f"cash-flow-statement/{fmp_symbol}", {"limit": 1})
        if cf_status != 200 or not cf_data or not isinstance(cf_data, list):
            return FundamentalResult(status=self._http_to_provider_status(cf_status), provider="FMP", http_status=cf_status)

        # 5. Fetch Key Metrics (Ratios)
        metrics_status, metrics_data = self._get(f"key-metrics/{fmp_symbol}", {"limit": 1})
        if metrics_status != 200 or not metrics_data or not isinstance(metrics_data, list):
            return FundamentalResult(status=self._http_to_provider_status(metrics_status), provider="FMP", http_status=metrics_status)

        # Parse the latest periods
        current_inc = inc_data[0]
        prev_inc = inc_data[1] if len(inc_data) > 1 else {}
        current_bs = bs_data[0]
        current_cf = cf_data[0]
        current_metrics = metrics_data[0]

        rev_growth = None
        if prev_inc.get("revenue") and current_inc.get("revenue"):
            rev_growth = (current_inc["revenue"] - prev_inc["revenue"]) / abs(prev_inc["revenue"])
            
        ni_growth = None
        if prev_inc.get("netIncome") and current_inc.get("netIncome"):
            ni_growth = (current_inc["netIncome"] - prev_inc["netIncome"]) / abs(prev_inc["netIncome"])

        return FundamentalResult(
            status=FundamentalProviderStatus.AVAILABLE,
            provider="FMP",
            http_status=200,
            isin=isin,
            symbol=symbol,
            provider_ticker=fmp_symbol,
            company_name=company_name or current_inc.get("symbol", fmp_symbol),
            identity_verified=identity_verified,
            revenue=current_inc.get("revenue"),
            revenue_growth=rev_growth,
            operating_profit=current_inc.get("operatingIncome"),
            net_profit=current_inc.get("netIncome"),
            profit_growth=ni_growth,
            eps=current_inc.get("eps"),
            roe=current_metrics.get("roe"),
            debt_to_equity=current_metrics.get("debtToEquity"),
            free_cash_flow=current_cf.get("freeCashFlow"),
            pe_ratio=current_metrics.get("peRatio"),
            book_value=current_metrics.get("pbRatio"),
            market_cap=current_metrics.get("marketCap"),
            dividend_yield=current_metrics.get("dividendYield"),
            timestamp=datetime.utcnow().isoformat(),
            available_fields=["revenue", "net_profit"]
        )
