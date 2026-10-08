"""
test_eodhd_fundamentals_once.py
================================
DIAGNOSTIC SCRIPT — READ-ONLY, NO ORDERS, NO MOCK DATA.

Validates the EODHD Fundamental Data Provider against a real
NSE-listed Indian company from the existing Angel One portfolio.

Safety:
  - Does NOT place any order.
  - Does NOT enable live trading.
  - Does NOT print the API token.
  - Does NOT use mock data.
  - Does NOT modify production code.

Usage:
  python test_eodhd_fundamentals_once.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# --- Make sure project root is on sys.path ---
ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Load .env before importing anything else
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass  # python-dotenv optional; token must already be in environment

# ---------------------------------------------------------------------------

from app.services.fundamentals.eodhd import (
    EODHDFundamentalDataProvider,
    FundamentalProviderStatus,
)


# ---------------------------------------------------------------------------
# Test target — use HEROMOTORS (Hero MotoCorp), a well-known NSE company
# Angel One symbol: HEROMOTORS-EQ
# ISIN from NSE: INE158A01026
# EODHD expected ticker: HEROMOTOCO.NSE
# ---------------------------------------------------------------------------
TEST_SYMBOL    = "HEROMOTORS-EQ"
TEST_ISIN      = "INE158A01026"   # Hero MotoCorp Ltd — NSE ISIN
TEST_EXCHANGE  = "NSE"

# ---------------------------------------------------------------------------

def _banner(title: str, width: int = 60) -> None:
    print("=" * width)
    print(f" {title}")
    print("=" * width)


def _section(title: str) -> None:
    print(f"\n--- {title} ---")


def main() -> None:
    _banner("EODHD FUNDAMENTAL PROVIDER TEST")
    print(f"Provider : EODHD")
    print(f"Data     : REAL")
    print(f"Mode     : READ-ONLY DIAGNOSTIC")
    print()

    # ----- Safety guards check -----
    enable_live = os.environ.get("ENABLE_LIVE_TRADING", "false").lower()
    exec_blocked = os.environ.get("BROKER_EXECUTION_BLOCKED", "true").lower()
    live_unlocked = os.environ.get("LIVE_EXECUTION_UNLOCKED", "false").lower()

    print(f"ENABLE_LIVE_TRADING      : {enable_live.upper()}")
    print(f"BROKER_EXECUTION_BLOCKED : {exec_blocked.upper()}")
    print(f"LIVE_EXECUTION_UNLOCKED  : {live_unlocked.upper()}")

    if enable_live == "true" or live_unlocked == "true":
        print("\n[HARD STOP] Live trading is enabled. This script must not run in live mode.")
        sys.exit(1)

    # ----- Token presence check (no value printed) -----
    _section("Authentication")
    token = os.environ.get("EODHD_API_TOKEN", "")
    if not token or token.lower() in {"placeholder", "your_real_eodhd_token_here", "none", ""}:
        print("Authentication : FAIL")
        print("Reason         : EODHD_API_TOKEN is missing or placeholder.")
        print()
        print("To use this script:")
        print("  1. Register at https://eodhd.com/r/eodhd-api")
        print("  2. Obtain your API token from the dashboard.")
        print("  3. Set in .env:  EODHD_API_TOKEN=<your_token>")
        print("  (Do NOT paste the token into this chat)")
        print()
        print("HARD STOP: No token — cannot validate provider.")
        sys.exit(0)

    # Token exists — show only first 4 chars as confirmation
    visible = token[:4] + ("*" * (len(token) - 4)) if len(token) > 4 else "****"
    print(f"Authentication : Token present ({visible})")

    # ----- Company under test -----
    _section("Test Target")
    print(f"Angel One Symbol : {TEST_SYMBOL}")
    print(f"ISIN             : {TEST_ISIN}")
    print(f"Exchange         : {TEST_EXCHANGE}")

    # ----- Run provider -----
    _section("Fetching Fundamentals")
    provider = EODHDFundamentalDataProvider()
    result = provider.get_fundamentals(
        symbol=TEST_SYMBOL,
        exchange=TEST_EXCHANGE,
        isin=TEST_ISIN,
    )

    # ----- Print results -----
    _section("Provider Response")
    print(f"Status           : {result.status.value}")
    print(f"HTTP Status      : {result.http_status}")
    print(f"EODHD Ticker     : {result.eodhd_ticker or 'NOT RESOLVED'}")
    print(f"Company Name     : {result.company_name or 'UNAVAILABLE'}")
    print(f"ISIN (returned)  : {result.isin or 'UNAVAILABLE'}")
    print(f"Identity Verified: {'YES' if result.identity_verified else 'NO'}")
    print(f"Timestamp        : {result.timestamp}")

    if result.error_message:
        print(f"Error            : {result.error_message}")

    if result.status == FundamentalProviderStatus.AUTH_ERROR:
        print("\nAuthentication : FAIL — Invalid or expired EODHD token.")
        sys.exit(1)
    elif result.status == FundamentalProviderStatus.RATE_LIMITED:
        print("\nRate limited by EODHD. Try again later.")
        sys.exit(0)
    elif result.status == FundamentalProviderStatus.NOT_FOUND:
        print("\nCompany not found on EODHD for this ticker/ISIN.")
        sys.exit(0)
    elif result.status != FundamentalProviderStatus.AVAILABLE:
        print(f"\nFundamentals: UNAVAILABLE ({result.status.value})")
        sys.exit(0)

    # ----- Available fields -----
    _section("Available Metrics")
    METRIC_MAP = [
        ("Revenue",              result.revenue,           "INR"),
        ("Revenue Growth",       result.revenue_growth,    "%"),
        ("Operating Profit",     result.operating_profit,  "INR"),
        ("Net Profit",           result.net_profit,        "INR"),
        ("Profit Growth",        result.profit_growth,     "%"),
        ("EPS",                  result.eps,               "INR"),
        ("EPS Growth",           result.eps_growth,        "%"),
        ("ROE",                  result.roe,               "%"),
        ("ROA",                  result.roa,               "%"),
        ("ROCE",                 result.roce,              "%"),
        ("Debt to Equity",       result.debt_to_equity,    "x"),
        ("Free Cash Flow",       result.free_cash_flow,    "INR"),
        ("P/E Ratio",            result.pe_ratio,          "x"),
        ("Book Value",           result.book_value,        "INR"),
        ("Market Cap",           result.market_cap,        "INR"),
        ("PEG Ratio",            result.peg_ratio,         "x"),
        ("Dividend Yield",       result.dividend_yield,    "%"),
    ]

    avail_count = 0
    unavail_count = 0
    for label, val, unit in METRIC_MAP:
        if val is not None:
            print(f"  {label:<22} : {val:>15.4f}  {unit}")
            avail_count += 1
        else:
            unavail_count += 1

    _section("Unavailable Metrics")
    for label, val, unit in METRIC_MAP:
        if val is None:
            print(f"  {label:<22} : UNAVAILABLE")

    # ----- Summary -----
    _section("Summary")
    print(f"Fundamentals         : {'AVAILABLE' if result.status == FundamentalProviderStatus.AVAILABLE else 'UNAVAILABLE'}")
    print(f"Fields Available     : {avail_count}/{len(METRIC_MAP)}")
    print(f"Fields Unavailable   : {unavail_count}/{len(METRIC_MAP)}")
    print(f"Identity Verified    : {'YES (ISIN matched)' if result.identity_verified else 'NO (unverified — no ISIN in response)'}")

    # ----- Integration suitability -----
    _section("Integration Suitability")
    MINIMUM_FIELDS_REQUIRED = 4  # at least P/E, ROE, EPS, net_profit
    critical = ["pe_ratio", "roe", "eps", "net_profit"]
    critical_present = [f for f in critical if getattr(result, f) is not None]
    if len(critical_present) >= MINIMUM_FIELDS_REQUIRED:
        print("EODHD provides sufficient fundamental data for integration.")
        print("Recommendation: PROCEED to integration phase.")
    else:
        print(f"EODHD provides only {avail_count} fields — minimum {MINIMUM_FIELDS_REQUIRED} critical required.")
        print("Recommendation: HARD STOP — insufficient data for integration.")

    print()
    _banner("END OF DIAGNOSTIC")


if __name__ == "__main__":
    main()
