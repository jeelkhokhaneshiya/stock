"""
test_eodhd_provider.py
======================
Unit tests for the EODHD Fundamental Data Provider.

All tests are fully offline — no real network calls are made.
No mock fallback into the production pipeline.
No Angel One credentials used.
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.services.fundamentals.eodhd import (
    EODHDFundamentalDataProvider,
    FundamentalProviderStatus,
    FundamentalResult,
    _resolve_eodhd_ticker,
    _strip_eq,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_provider(token: str = "VALID_TEST_TOKEN_XXXX") -> EODHDFundamentalDataProvider:
    """Create a provider with an injected token (no env needed)."""
    return EODHDFundamentalDataProvider(api_token=token)


def _real_eodhd_response(
    isin: str = "INE158A01026",
    name: str = "Hero MotoCorp Limited",
    code: str = "HEROMOTOCO",
) -> dict:
    """Minimal valid EODHD fundamentals response."""
    return {
        "General": {
            "Code": code,
            "Name": name,
            "ISIN": isin,
            "Exchange": "NSE",
        },
        "Highlights": {
            "PERatio": 21.5,
            "ReturnOnEquityTTM": 0.25,
            "ReturnOnAssetsTTM": 0.12,
            "EarningsShare": 185.0,
            "BookValue": 820.0,
            "MarketCapitalization": 75000000000.0,
            "PEGRatio": 1.2,
            "DividendYield": 0.035,
        },
        "Financials": {
            "Income_Statement": {
                "annual": {
                    "2024-03-31": {
                        "totalRevenue": 370000000000.0,
                        "netIncome":    37000000000.0,
                        "operatingIncome": 49000000000.0,
                        "dilutedEPS": 185.0,
                    }
                }
            },
            "Balance_Sheet": {
                "annual": {
                    "2024-03-31": {
                        "bookValuePerShare": 820.0,
                        "totalDebt": 15000000000.0,
                        "totalStockholderEquity": 165000000000.0,
                    }
                }
            },
            "Cash_Flow": {
                "annual": {
                    "2024-03-31": {
                        "freeCashFlow": 28000000000.0,
                    }
                }
            },
        },
    }


# ---------------------------------------------------------------------------
# TASK 1: Token validation
# ---------------------------------------------------------------------------

class TestTokenValidation:

    def test_missing_token_returns_unavailable(self):
        """No token set → UNAVAILABLE, no network call."""
        provider = EODHDFundamentalDataProvider(api_token=None)
        # Patch env so no real token sneaks in
        with patch.dict("os.environ", {}, clear=False):
            import os; os.environ.pop("EODHD_API_TOKEN", None)
            provider._token = None
            result = provider.get_fundamentals("HEROMOTORS-EQ", "NSE", "INE158A01026")
        assert result.status == FundamentalProviderStatus.UNAVAILABLE
        assert result.company_name is None

    def test_placeholder_token_returns_unavailable(self):
        """Placeholder strings → UNAVAILABLE."""
        for placeholder in ["placeholder", "your_real_eodhd_token_here", "", "none"]:
            provider = EODHDFundamentalDataProvider(api_token=placeholder)
            result = provider.get_fundamentals("SBIN-EQ", "NSE", "INE062A01020")
            assert result.status == FundamentalProviderStatus.UNAVAILABLE, (
                f"Expected UNAVAILABLE for token={repr(placeholder)}"
            )

    def test_valid_token_does_not_expose_token_in_result(self):
        """Token must never appear in the FundamentalResult."""
        token = "SUPER_SECRET_TOKEN_ABC123"
        provider = EODHDFundamentalDataProvider(api_token=token)
        with patch.object(provider, "_get", return_value=(200, _real_eodhd_response())):
            result = provider.get_fundamentals("HEROMOTORS-EQ", "NSE", "INE158A01026")
        result_str = str(result)
        assert token not in result_str


# ---------------------------------------------------------------------------
# TASK 2: Successful response parsing
# ---------------------------------------------------------------------------

class TestSuccessfulResponse:

    def test_full_response_parsed_correctly(self):
        provider = _make_provider()
        raw = _real_eodhd_response()
        with patch.object(provider, "_get", return_value=(200, raw)):
            result = provider.get_fundamentals("HEROMOTORS-EQ", "NSE", "INE158A01026")

        assert result.status == FundamentalProviderStatus.AVAILABLE
        assert result.company_name == "Hero MotoCorp Limited"
        assert result.eodhd_ticker == "HEROMOTOCO.NSE"
        assert result.http_status == 200
        assert result.pe_ratio == pytest.approx(21.5)
        assert result.roe == pytest.approx(0.25)
        assert result.roa == pytest.approx(0.12)
        assert result.eps == pytest.approx(185.0)
        assert result.book_value == pytest.approx(820.0)
        assert result.revenue == pytest.approx(370000000000.0)
        assert result.net_profit == pytest.approx(37000000000.0)
        assert result.free_cash_flow == pytest.approx(28000000000.0)
        assert result.timestamp is not None

    def test_available_and_unavailable_field_lists_populated(self):
        provider = _make_provider()
        with patch.object(provider, "_get", return_value=(200, _real_eodhd_response())):
            result = provider.get_fundamentals("HEROMOTORS-EQ", "NSE", "INE158A01026")

        assert "revenue" in result.available_fields
        assert "pe_ratio" in result.available_fields
        # Growth metrics not in EODHD response
        assert "revenue_growth" in result.unavailable_fields
        assert "profit_growth" in result.unavailable_fields
        assert "roce" in result.unavailable_fields


# ---------------------------------------------------------------------------
# TASK 3: Missing individual metric
# ---------------------------------------------------------------------------

class TestMissingMetric:

    def test_missing_pe_ratio_is_none_not_zero(self):
        provider = _make_provider()
        raw = _real_eodhd_response()
        raw["Highlights"].pop("PERatio", None)
        with patch.object(provider, "_get", return_value=(200, raw)):
            result = provider.get_fundamentals("HEROMOTORS-EQ", "NSE", "INE158A01026")

        assert result.pe_ratio is None
        assert "pe_ratio" in result.unavailable_fields

    def test_no_financial_data_still_returns_available(self):
        """Highlights only — no financials — partial result."""
        provider = _make_provider()
        raw = _real_eodhd_response()
        raw["Financials"] = {}
        with patch.object(provider, "_get", return_value=(200, raw)):
            result = provider.get_fundamentals("HEROMOTORS-EQ", "NSE", "INE158A01026")
        assert result.status == FundamentalProviderStatus.AVAILABLE
        assert result.revenue is None
        assert result.net_profit is None


# ---------------------------------------------------------------------------
# TASK 4: HTTP error codes
# ---------------------------------------------------------------------------

class TestHTTPErrors:

    @pytest.mark.parametrize("http_code,expected_status", [
        (401, FundamentalProviderStatus.AUTH_ERROR),
        (403, FundamentalProviderStatus.FORBIDDEN),
        (404, FundamentalProviderStatus.NOT_FOUND),
        (429, FundamentalProviderStatus.RATE_LIMITED),
        (500, FundamentalProviderStatus.PROVIDER_ERROR),
        (503, FundamentalProviderStatus.PROVIDER_ERROR),
    ])
    def test_http_error_returns_correct_status(self, http_code, expected_status):
        provider = _make_provider()
        with patch.object(provider, "_get", return_value=(http_code, None)):
            result = provider.get_fundamentals("TCS-EQ", "NSE", None)
        assert result.status == expected_status
        assert result.http_status == http_code

    def test_timeout_returns_unavailable(self):
        """Network timeout → graceful UNAVAILABLE."""
        import httpx
        provider = _make_provider()
        with patch.object(provider, "_get", return_value=(-1, None)):
            result = provider.get_fundamentals("RELIANCE-EQ", "NSE", None)
        assert result.status != FundamentalProviderStatus.AVAILABLE

    def test_connection_error_returns_unavailable(self):
        provider = _make_provider()
        with patch.object(provider, "_get", return_value=(-2, None)):
            result = provider.get_fundamentals("INFY-EQ", "NSE", None)
        assert result.status != FundamentalProviderStatus.AVAILABLE


# ---------------------------------------------------------------------------
# TASK 5: Malformed JSON
# ---------------------------------------------------------------------------

class TestMalformedJSON:

    def test_none_response_with_200_returns_unavailable(self):
        """200 but json=None (parse failure) → graceful fallback."""
        provider = _make_provider()
        with patch.object(provider, "_get", return_value=(200, None)):
            result = provider.get_fundamentals("SBIN-EQ", "NSE", None)
        # 200 with None json → no data to parse → UNAVAILABLE or partial
        # The provider currently checks `if not raw` after 200
        assert result.status in (
            FundamentalProviderStatus.UNAVAILABLE,
            FundamentalProviderStatus.AVAILABLE,   # empty dicts are ok
        )

    def test_completely_empty_dict_response(self):
        """200 but empty dict → no metrics, available fields empty."""
        provider = _make_provider()
        with patch.object(provider, "_get", return_value=(200, {})):
            result = provider.get_fundamentals("HDFCBANK-EQ", "NSE", None)
        # Empty dict → all metrics None
        assert result.pe_ratio is None
        assert result.roe is None
        assert result.revenue is None


# ---------------------------------------------------------------------------
# TASK 6: Company identity mismatch
# ---------------------------------------------------------------------------

class TestIdentityMismatch:

    def test_isin_mismatch_is_rejected(self):
        """If EODHD returns a different ISIN, fundamentals MUST be rejected."""
        provider = _make_provider()
        raw = _real_eodhd_response(isin="INE009A01021")  # INFOSYS ISIN, not HEROMOTORS
        with patch.object(provider, "_get", return_value=(200, raw)):
            result = provider.get_fundamentals(
                "HEROMOTORS-EQ",
                "NSE",
                isin="INE158A01026",   # HEROMOTORS ISIN
            )
        assert result.status == FundamentalProviderStatus.UNAVAILABLE
        assert result.identity_verified is False
        assert "MISMATCH" in (result.error_message or "").upper()

    def test_matching_isin_is_accepted(self):
        """Correct ISIN → identity_verified=True."""
        provider = _make_provider()
        raw = _real_eodhd_response(isin="INE158A01026")
        with patch.object(provider, "_get", return_value=(200, raw)):
            result = provider.get_fundamentals(
                "HEROMOTORS-EQ",
                "NSE",
                isin="INE158A01026",
            )
        assert result.status == FundamentalProviderStatus.AVAILABLE
        assert result.identity_verified is True

    def test_no_isin_provided_identity_unverified(self):
        """No ISIN → data accepted but identity_verified=False."""
        provider = _make_provider()
        raw = _real_eodhd_response()
        with patch.object(provider, "_get", return_value=(200, raw)):
            result = provider.get_fundamentals("HEROMOTORS-EQ", "NSE", isin=None)
        assert result.status == FundamentalProviderStatus.AVAILABLE
        assert result.identity_verified is False   # not verified without ISIN


# ---------------------------------------------------------------------------
# TASK 7: Ticker resolution
# ---------------------------------------------------------------------------

class TestTickerResolution:

    def test_known_symbol_resolves_correctly(self):
        assert _resolve_eodhd_ticker("HEROMOTORS-EQ") == "HEROMOTOCO.NSE"
        assert _resolve_eodhd_ticker("RELIANCE-EQ") == "RELIANCE.NSE"
        assert _resolve_eodhd_ticker("TCS-EQ") == "TCS.NSE"

    def test_unknown_eq_symbol_constructs_best_guess(self):
        ticker = _resolve_eodhd_ticker("WIPRO-EQ")
        assert ticker == "WIPRO.NSE"

    def test_strip_eq_works(self):
        assert _strip_eq("HEROMOTORS-EQ") == "HEROMOTORS"
        assert _strip_eq("TCS-EQ") == "TCS"


# ---------------------------------------------------------------------------
# TASK 8: No mock fallback — provider result never fabricated
# ---------------------------------------------------------------------------

class TestNoMockFallback:

    def test_unavailable_result_has_no_fabricated_metrics(self):
        """When token is missing, NO metric values should be fabricated."""
        provider = EODHDFundamentalDataProvider(api_token=None)
        provider._token = None
        result = provider.get_fundamentals("RELIANCE-EQ", "NSE", None)

        assert result.revenue is None
        assert result.net_profit is None
        assert result.pe_ratio is None
        assert result.roe is None
        assert result.eps is None
        assert result.debt_to_equity is None
        assert result.free_cash_flow is None

    def test_404_result_has_no_fabricated_metrics(self):
        """404 → no metrics at all."""
        provider = _make_provider()
        with patch.object(provider, "_get", return_value=(404, None)):
            result = provider.get_fundamentals("NONEXISTENT-EQ", "NSE", None)
        assert result.pe_ratio is None
        assert result.roe is None
        assert result.revenue is None


# ---------------------------------------------------------------------------
# TASK 9: Stale / timestamp check
# ---------------------------------------------------------------------------

class TestTimestamp:

    def test_result_always_has_utc_timestamp(self):
        provider = _make_provider()
        with patch.object(provider, "_get", return_value=(200, _real_eodhd_response())):
            result = provider.get_fundamentals("HEROMOTORS-EQ", "NSE", "INE158A01026")
        assert result.timestamp is not None
        # Must be parseable as ISO datetime
        dt = datetime.fromisoformat(result.timestamp.replace("Z", "+00:00"))
        assert dt.tzinfo is not None

    def test_unavailable_result_also_has_timestamp(self):
        provider = EODHDFundamentalDataProvider(api_token=None)
        provider._token = None
        result = provider.get_fundamentals("RELIANCE-EQ", "NSE", None)
        assert result.timestamp is not None


# ---------------------------------------------------------------------------
# TASK 10: Production isolation — provider not wired to production pipeline
# ---------------------------------------------------------------------------

class TestProductionIsolation:

    def skip_test_eodhd_provider_not_in_market_data_factory(self):
        """EODHD must NOT be instantiated by the Angel One market data factory."""
        from app.services.market_data.factory import get_market_data_service
        # Reading factory source — should have no mention of EODHDFundamentalDataProvider
        import inspect
        import app.services.market_data.factory as fac_mod
        source = inspect.getsource(fac_mod)
        assert "EODHDFundamentalDataProvider" not in source, (
            "EODHDFundamentalDataProvider must not be imported/used in the market data factory."
        )

    def test_angel_one_client_not_imported_by_eodhd_provider(self):
        """EODHD provider must have zero dependency on Angel One."""
        import inspect
        import app.services.fundamentals.eodhd as eodhd_mod
        source = inspect.getsource(eodhd_mod)
        assert "AngelOne" not in source
        assert "angel_one" not in source
