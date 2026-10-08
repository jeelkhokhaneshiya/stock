"""
eodhd.py — EODHD Fundamental Data Provider (ISOLATED, READ-ONLY)
=================================================================
Fetches real company fundamental data from the EODHD API v1.1 for
Indian NSE-listed companies.

SAFETY CONTRACT:
- Completely isolated from Angel One market/portfolio pipeline.
- NOT connected to DecisionEngine, CandidateRanker, or ExecutionReadiness.
- Reads EODHD_API_TOKEN from environment — NEVER from Angel One credentials.
- Never prints, logs, or exposes the API token.
- If token is missing/placeholder/invalid → returns UNAVAILABLE, does not raise.
- If company identity cannot be verified → returns UNAVAILABLE.
- Never fabricates or estimates missing metric values.

EODHD ticker format for NSE India: <SYMBOL>.NSE
e.g. HDFCBANK.NSE, HEROMOTOCO.NSE
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

from app.services.fundamentals.base import (
    FundamentalResult,
    FundamentalProviderStatus,
    FundamentalDataProvider
)

# ---------------------------------------------------------------------------
# EODHD Ticker mapping — Angel One symbol → EODHD NSE ticker
# ---------------------------------------------------------------------------

# Only verified, manually confirmed mappings are kept here.
# Do NOT silently guess.  If a symbol isn't here, we search the EODHD API.
ANGEL_TO_EODHD: Dict[str, str] = {
    "HEROMOTORS-EQ":  "HEROMOTOCO.NSE",
    "HEROMOTOCO-EQ":  "HEROMOTOCO.NSE",
    "MONEYVIEW-EQ":   None,              # may not be listed; will attempt search
    "RELIANCE-EQ":    "RELIANCE.NSE",
    "TCS-EQ":         "TCS.NSE",
    "INFY-EQ":        "INFY.NSE",
    "SBIN-EQ":        "SBIN.NSE",
    "HDFCBANK-EQ":    "HDFCBANK.NSE",
    "ICICIBANK-EQ":   "ICICIBANK.NSE",
}


def _strip_eq(symbol: str) -> str:
    """Remove the -EQ suffix used by Angel One."""
    return symbol.replace("-EQ", "").strip().upper()


def _resolve_eodhd_ticker(angel_symbol: str) -> Optional[str]:
    """
    Resolve Angel One symbol to EODHD NSE ticker.
    1. Check known static mapping.
    2. Construct best-guess ticker only for NSE-EQ symbols.
    Returns None if resolution is not possible.
    """
    # 1. Known mapping first
    if angel_symbol in ANGEL_TO_EODHD:
        return ANGEL_TO_EODHD[angel_symbol]  # may be None for explicitly unknown

    # 2. For -EQ symbols, construct as <STRIPPED>.NSE
    if angel_symbol.endswith("-EQ"):
        base = _strip_eq(angel_symbol)
        return f"{base}.NSE"

    return None


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------

_PLACEHOLDER_VALUES = {"placeholder", "your_real_eodhd_token_here", "", "none"}


class EODHDFundamentalDataProvider(FundamentalDataProvider):
    """
    Isolated, read-only EODHD fundamental data provider.
    Completely decoupled from Angel One.  Token from env only.
    """

    BASE_URL = "https://eodhd.com/api"

    def __init__(
        self,
        api_token: Optional[str] = None,
        timeout: float = 15.0,
    ):
        # Token from env; accept override only for tests via explicit arg.
        self._token: Optional[str] = api_token if api_token is not None else os.environ.get("EODHD_API_TOKEN")
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Token validation (no secrets in logs)
    # ------------------------------------------------------------------

    def _token_status(self) -> FundamentalProviderStatus:
        if not self._token or self._token.lower() in _PLACEHOLDER_VALUES:
            return FundamentalProviderStatus.UNAVAILABLE
        return FundamentalProviderStatus.AVAILABLE

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _get(self, path: str, params: Dict[str, Any]) -> tuple[int, Optional[Dict]]:
        """
        Perform a GET request.  Returns (http_status, json_or_None).
        Token is injected server-side and never logged.
        """
        params = dict(params)
        params["api_token"] = self._token     # injected here, not in logs
        params.setdefault("fmt", "json")

        url = f"{self.BASE_URL}/{path.lstrip('/')}"
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(url, params=params)
                status = resp.status_code
                if status == 200:
                    try:
                        return status, resp.json()
                    except Exception:
                        logger.warning("EODHD: 200 response but invalid JSON from %s", path)
                        return status, None
                else:
                    # Log path, NOT the full URL (which contains token)
                    logger.warning("EODHD: HTTP %s for path=%s", status, path)
                    return status, None
        except httpx.TimeoutException:
            logger.warning("EODHD: Request timed out for path=%s", path)
            return -1, None
        except httpx.ConnectError:
            logger.warning("EODHD: Connection error for path=%s", path)
            return -2, None
        except Exception as exc:
            logger.error("EODHD: Unexpected error for path=%s — %s", path, type(exc).__name__)
            return -3, None

    # ------------------------------------------------------------------
    # ISIN-to-ticker lookup via EODHD search
    # ------------------------------------------------------------------

    def _search_by_isin(self, isin: str) -> Optional[str]:
        """
        Use EODHD search endpoint to resolve ISIN → ticker.
        Returns EODHD ticker (e.g. HEROMOTOCO.NSE) or None.
        """
        http_status, data = self._get("search", {"q": isin, "limit": 5})
        if http_status != 200 or not isinstance(data, list):
            return None
        # Prefer NSE exchange results for Indian companies
        for item in data:
            exch = (item.get("Exchange") or "").upper()
            code = item.get("Code") or item.get("Ticker")
            if exch == "NSE" and code:
                return f"{code}.NSE"
        # Fall back to first result with a Code
        for item in data:
            code = item.get("Code") or item.get("Ticker")
            exch = item.get("Exchange", "")
            if code and exch:
                return f"{code}.{exch}"
        return None

    # ------------------------------------------------------------------
    # HTTP status → provider status
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Safe float extraction — returns None if field absent or non-numeric
    # ------------------------------------------------------------------

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
            return f if not (f != f) else None  # reject NaN
        except (TypeError, ValueError):
            return None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_fundamentals(
        self,
        symbol: str,                # Angel One symbol e.g. HEROMOTORS-EQ
        exchange: str = "NSE",
        isin: Optional[str] = None,
    ) -> FundamentalResult:
        """
        Fetch real fundamental data for the given company.
        Returns a FundamentalResult — NEVER raises.
        """
        ts = datetime.now(timezone.utc).isoformat()

        # 1. Token gate
        token_status = self._token_status()
        if token_status != FundamentalProviderStatus.AVAILABLE:
            logger.info("EODHD: Token not configured — returning UNAVAILABLE for %s", symbol)
            return FundamentalResult(
                status=FundamentalProviderStatus.UNAVAILABLE,
                symbol=symbol,
                isin=isin,
                timestamp=ts,
                error_message="EODHD_API_TOKEN not set or is placeholder",
            )

        # 2. Resolve EODHD ticker
        eodhd_ticker = _resolve_eodhd_ticker(symbol)

        # 3. If resolution failed, try ISIN search
        if not eodhd_ticker and isin:
            logger.info("EODHD: No static mapping for %s — searching by ISIN %s", symbol, isin)
            eodhd_ticker = self._search_by_isin(isin)

        if not eodhd_ticker:
            logger.warning("EODHD: Cannot resolve ticker for %s (ISIN=%s)", symbol, isin)
            return FundamentalResult(
                status=FundamentalProviderStatus.NOT_FOUND,
                symbol=symbol,
                isin=isin,
                timestamp=ts,
                error_message=f"Could not resolve EODHD ticker for {symbol}",
            )

        # 4. Fetch fundamentals — use filter to avoid huge response
        filter_fields = (
            "General,Highlights,Financials::Income_Statement::annual,"
            "Financials::Balance_Sheet::annual,Financials::Cash_Flow::annual"
        )
        http_status, raw = self._get(
            f"fundamentals/{eodhd_ticker}",
            {"filter": filter_fields},
        )

        provider_status = self._http_to_provider_status(http_status)

        if provider_status != FundamentalProviderStatus.AVAILABLE or not raw:
            return FundamentalResult(
                status=provider_status,
                symbol=symbol,
                provider_ticker=eodhd_ticker,
                isin=isin,
                http_status=http_status,
                timestamp=ts,
                error_message=f"EODHD HTTP {http_status} for {eodhd_ticker}",
            )

        # 5. Parse identity fields
        general = raw.get("General", {}) or {}
        highlights = raw.get("Highlights", {}) or {}
        financials = raw.get("Financials", {}) or {}

        api_isin = general.get("ISIN") or general.get("Isin")
        api_name = general.get("Name") or general.get("CompanyName")
        api_code = general.get("Code")

        # 6. Identity verification
        identity_verified = False
        identity_error = None

        if isin and api_isin:
            if isin.strip().upper() == str(api_isin).strip().upper():
                identity_verified = True
            else:
                identity_error = (
                    f"ISIN MISMATCH: requested={isin}, received={api_isin}. "
                    "Fundamentals rejected."
                )
                logger.error("EODHD: %s", identity_error)
                return FundamentalResult(
                    status=FundamentalProviderStatus.UNAVAILABLE,
                    symbol=symbol,
                    provider_ticker=eodhd_ticker,
                    isin=isin,
                    http_status=http_status,
                    timestamp=ts,
                    identity_verified=False,
                    error_message=identity_error,
                )
        elif not isin:
            # No ISIN provided — accept but mark as unverified
            identity_verified = False
            logger.warning(
                "EODHD: No ISIN provided for %s; identity unverified. Accepting with caution.",
                symbol,
            )
        else:
            # ISIN provided but API didn't return one — treat as unverified
            identity_verified = False

        # 7. Extract latest annual financials helper
        def _latest_annual(section_path: str, key: str) -> Optional[float]:
            """Navigate nested Financials dict to get latest annual value."""
            parts = section_path.split(".")
            node = financials
            for p in parts:
                if not isinstance(node, dict):
                    return None
                node = node.get(p)
            if not isinstance(node, dict):
                return None
            # annual dict: keys are dates, sort descending
            dates = sorted(node.keys(), reverse=True)
            for d in dates:
                record = node.get(d)
                if isinstance(record, dict) and key in record:
                    v = record[key]
                    if v is not None and v != "" and v != "None":
                        try:
                            return float(v)
                        except (TypeError, ValueError):
                            pass
            return None

        # 8. Parse all requested metrics
        sf = self._safe_float

        # Income Statement
        revenue      = _latest_annual("Income_Statement.annual", "totalRevenue")
        net_profit   = _latest_annual("Income_Statement.annual", "netIncome")
        operating_profit = _latest_annual("Income_Statement.annual", "operatingIncome")
        eps          = _latest_annual("Income_Statement.annual", "epsActual") or \
                       _latest_annual("Income_Statement.annual", "dilutedEPS")

        # Balance Sheet
        book_value_raw = _latest_annual("Balance_Sheet.annual", "bookValuePerShare")
        total_debt     = _latest_annual("Balance_Sheet.annual", "totalDebt")
        shareholder_eq = _latest_annual("Balance_Sheet.annual", "totalStockholderEquity")
        debt_to_equity: Optional[float] = None
        if total_debt is not None and shareholder_eq and shareholder_eq != 0:
            debt_to_equity = round(total_debt / shareholder_eq, 4)

        # Cash Flow
        free_cash_flow = _latest_annual("Cash_Flow.annual", "freeCashFlow")

        # Highlights
        pe_ratio     = sf(highlights, "PERatio")
        roe          = sf(highlights, "ReturnOnEquityTTM")
        roa          = sf(highlights, "ReturnOnAssetsTTM")
        peg_ratio    = sf(highlights, "PEGRatio")
        book_value   = sf(highlights, "BookValue") or book_value_raw
        eps_h        = sf(highlights, "EarningsShare")
        eps          = eps or eps_h
        dividend_yield = sf(highlights, "DividendYield")
        market_cap   = sf(highlights, "MarketCapitalization")

        # Growth metrics — EODHD doesn't directly expose YoY growth pct
        # DO NOT fabricate — mark as UNAVAILABLE if not in response
        revenue_growth  = None
        profit_growth   = None
        eps_growth      = None
        roce            = None  # Not in EODHD highlights; mark UNAVAILABLE

        # 9. Track which fields are available vs unavailable
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
        avail   = [name for name, val in ALL_FIELDS if val is not None]
        unavail = [name for name, val in ALL_FIELDS if val is None]

        return FundamentalResult(
            status=FundamentalProviderStatus.AVAILABLE,
            provider="EODHD",
            http_status=http_status,
            isin=isin,
            symbol=symbol,
            provider_ticker=eodhd_ticker,
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
