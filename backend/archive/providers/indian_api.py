"""
indian_api.py — IndianAPI Fundamental Data Provider (ISOLATED, READ-ONLY)
=================================================================
Fetches real company fundamental data from IndianAPI for NSE-listed companies.

SAFETY CONTRACT:
- Completely isolated from Angel One market/portfolio pipeline.
- NOT connected to DecisionEngine, CandidateRanker, or ExecutionReadiness.
- Reads INDIAN_API_KEY from environment.
- Never prints, logs, or exposes the API token.
- If token is missing/placeholder/invalid → returns UNAVAILABLE, does not raise.
- If company identity cannot be verified → returns UNAVAILABLE.
- Never fabricates or estimates missing metric values.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from app.services.fundamentals.base import FundamentalResult, FundamentalProviderStatus, FundamentalDataProvider
from app.services.fundamentals.eodhd import _strip_eq

logger = logging.getLogger(__name__)

_PLACEHOLDER_VALUES = {"placeholder", "your_indian_api_key_here", "", "none"}

# Known mappings for Angel One to NSE Symbol
ANGEL_TO_NSE: Dict[str, str] = {
    "HEROMOTORS-EQ":  "HEROMOTOCO",
    "HEROMOTOCO-EQ":  "HEROMOTOCO",
    "MONEYVIEW-EQ":   None,
    "RELIANCE-EQ":    "RELIANCE",
    "TCS-EQ":         "TCS",
    "INFY-EQ":        "INFY",
    "SBIN-EQ":        "SBIN",
    "HDFCBANK-EQ":    "HDFCBANK",
    "ICICIBANK-EQ":   "ICICIBANK",
}

def _resolve_nse_symbol(angel_symbol: str) -> Optional[str]:
    """Resolve Angel One symbol to NSE symbol."""
    if angel_symbol in ANGEL_TO_NSE:
        return ANGEL_TO_NSE[angel_symbol]
    if angel_symbol.endswith("-EQ"):
        return _strip_eq(angel_symbol)
    return None

class IndianAPIFundamentalDataProvider(FundamentalDataProvider):
    """
    Isolated, read-only IndianAPI fundamental data provider.
    Token from env only.
    """

    BASE_URL = "https://analyst.indianapi.in"

    def __init__(self, api_key: Optional[str] = None, timeout: float = 15.0):
        self._api_key: Optional[str] = api_key if api_key is not None else os.environ.get("INDIAN_API_KEY")
        self._timeout = timeout

    def _token_status(self) -> FundamentalProviderStatus:
        if not self._api_key or self._api_key.lower() in _PLACEHOLDER_VALUES:
            return FundamentalProviderStatus.UNAVAILABLE
        return FundamentalProviderStatus.AVAILABLE

    def _get(self, path: str, params: Dict[str, Any] = None) -> tuple[int, Optional[Dict]]:
        """Perform a GET request. Token is in headers."""
        url = f"{self.BASE_URL}/{path.lstrip('/')}"
        headers = {"X-API-Key": self._api_key} if self._api_key else {}
        params = params or {}
        
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(url, params=params, headers=headers)
                status = resp.status_code
                if status == 200:
                    try:
                        return status, resp.json()
                    except Exception:
                        logger.warning("IndianAPI: 200 response but invalid JSON from %s", path)
                        return status, None
                else:
                    logger.warning("IndianAPI: HTTP %s for path=%s", status, path)
                    return status, None
        except httpx.TimeoutException:
            logger.warning("IndianAPI: Request timed out for path=%s", path)
            return -1, None
        except httpx.ConnectError:
            logger.warning("IndianAPI: Connection error for path=%s", path)
            return -2, None
        except Exception as exc:
            logger.error("IndianAPI: Unexpected error for path=%s — %s", path, type(exc).__name__)
            return -3, None

    @staticmethod
    def _http_to_provider_status(http_status: int) -> FundamentalProviderStatus:
        if http_status == 200:
            return FundamentalProviderStatus.AVAILABLE
        if http_status in (401,):
            return FundamentalProviderStatus.AUTH_ERROR
        if http_status in (403,):
            return FundamentalProviderStatus.FORBIDDEN
        if http_status in (404,):
            return FundamentalProviderStatus.NOT_FOUND
        if http_status in (429,):
            return FundamentalProviderStatus.RATE_LIMITED
        if http_status >= 500:
            return FundamentalProviderStatus.PROVIDER_ERROR
        return FundamentalProviderStatus.UNAVAILABLE

    @staticmethod
    def _safe_float(data: Any, *keys: str) -> Optional[float]:
        if not isinstance(data, dict):
            return None
        val = data
        for k in keys:
            if not isinstance(val, dict):
                return None
            val = val.get(k)
        if val is None or val == "" or val == "None":
            return None
        try:
            f = float(val)
            return f if not (f != f) else None
        except (TypeError, ValueError):
            return None

    def get_fundamentals(
        self,
        symbol: str,
        exchange: str = "NSE",
        isin: Optional[str] = None,
    ) -> FundamentalResult:
        ts = datetime.now(timezone.utc).isoformat()
        
        token_status = self._token_status()
        if token_status != FundamentalProviderStatus.AVAILABLE:
            logger.info("IndianAPI: Token not configured — returning UNAVAILABLE for %s", symbol)
            return FundamentalResult(
                status=FundamentalProviderStatus.UNAVAILABLE,
                symbol=symbol,
                isin=isin,
                timestamp=ts,
                error_message="INDIAN_API_KEY not set or is placeholder",
            )
            
        nse_symbol = _resolve_nse_symbol(symbol)
        if not nse_symbol:
            logger.warning("IndianAPI: Cannot resolve ticker for %s", symbol)
            return FundamentalResult(
                status=FundamentalProviderStatus.NOT_FOUND,
                symbol=symbol,
                isin=isin,
                timestamp=ts,
                error_message=f"Could not resolve NSE symbol for {symbol}",
            )
            
        http_status, raw = self._get("stock", {"name": nse_symbol})
        provider_status = self._http_to_provider_status(http_status)
        
        if provider_status != FundamentalProviderStatus.AVAILABLE or not raw:
            final_status = provider_status if provider_status != FundamentalProviderStatus.AVAILABLE else FundamentalProviderStatus.UNAVAILABLE
            return FundamentalResult(
                status=final_status,
                symbol=symbol,
                provider_ticker=nse_symbol,
                isin=isin,
                http_status=http_status,
                timestamp=ts,
                error_message=f"IndianAPI HTTP {http_status} for {nse_symbol}",
            )
            
        # Parse data
        api_isin = raw.get("isin") or raw.get("ISIN")
        api_name = raw.get("companyName") or raw.get("name")
        
        identity_verified = False
        identity_error = None
        
        if isin and api_isin:
            if isin.strip().upper() == str(api_isin).strip().upper():
                identity_verified = True
            else:
                identity_error = f"ISIN MISMATCH: requested={isin}, received={api_isin}. Fundamentals rejected."
                logger.error("IndianAPI: %s", identity_error)
                return FundamentalResult(
                    status=FundamentalProviderStatus.UNAVAILABLE,
                    symbol=symbol,
                    provider_ticker=nse_symbol,
                    isin=isin,
                    http_status=http_status,
                    timestamp=ts,
                    identity_verified=False,
                    error_message=identity_error,
                )
        elif not isin:
            identity_verified = False
        else:
            identity_verified = False
            
        sf = self._safe_float
        revenue = sf(raw, "revenue")
        revenue_growth = sf(raw, "revenueGrowth")
        operating_profit = sf(raw, "operatingProfit")
        net_profit = sf(raw, "netProfit")
        profit_growth = sf(raw, "profitGrowth")
        eps = sf(raw, "eps")
        eps_growth = sf(raw, "epsGrowth")
        roe = sf(raw, "roe")
        roa = sf(raw, "roa")
        roce = sf(raw, "roce")
        debt_to_equity = sf(raw, "debtToEquity")
        free_cash_flow = sf(raw, "freeCashFlow")
        pe_ratio = sf(raw, "pe")
        book_value = sf(raw, "bookValue")
        market_cap = sf(raw, "marketCap")
        peg_ratio = sf(raw, "peg")
        dividend_yield = sf(raw, "dividendYield")
        
        ALL_FIELDS = [
            ("revenue", revenue),
            ("revenue_growth", revenue_growth),
            ("operating_profit", operating_profit),
            ("net_profit", net_profit),
            ("profit_growth", profit_growth),
            ("eps", eps),
            ("eps_growth", eps_growth),
            ("roe", roe),
            ("roa", roa),
            ("roce", roce),
            ("debt_to_equity", debt_to_equity),
            ("free_cash_flow", free_cash_flow),
            ("pe_ratio", pe_ratio),
            ("book_value", book_value),
            ("market_cap", market_cap),
            ("peg_ratio", peg_ratio),
            ("dividend_yield", dividend_yield),
        ]
        
        avail = [name for name, val in ALL_FIELDS if val is not None]
        unavail = [name for name, val in ALL_FIELDS if val is None]
        
        return FundamentalResult(
            status=FundamentalProviderStatus.AVAILABLE,
            provider="IndianAPI",
            http_status=http_status,
            isin=isin,
            symbol=symbol,
            provider_ticker=nse_symbol,
            company_name=api_name,
            identity_verified=identity_verified,
            revenue=revenue,
            revenue_growth=revenue_growth,
            operating_profit=operating_profit,
            net_profit=net_profit,
            profit_growth=profit_growth,
            eps=eps,
            eps_growth=eps_growth,
            roe=roe,
            roa=roa,
            roce=roce,
            debt_to_equity=debt_to_equity,
            free_cash_flow=free_cash_flow,
            pe_ratio=pe_ratio,
            book_value=book_value,
            market_cap=market_cap,
            peg_ratio=peg_ratio,
            dividend_yield=dividend_yield,
            timestamp=ts,
            available_fields=avail,
            unavailable_fields=unavail,
        )
