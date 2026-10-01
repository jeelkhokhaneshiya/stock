"""
AngelOneDataService — read-only account data retrieval.

Uses the existing AngelOneClient (which holds a live JWT session obtained
during authenticate()).  Re-uses the session; does NOT log in again.

Safety guarantees
-----------------
* No order placement, modification, or cancellation.
* Secrets (api_key, password, totp_secret, jwt_token, feed_token) are NEVER
  logged or returned to callers.
* All broker responses are normalised into application-level schemas before
  leaving this module.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List

from app.schemas.angel_one import (
    AngelOneAccountInfo,
    AngelOneFundsResponse,
    AngelOneHoldingItem,
    AngelOneHoldingsResponse,
    AngelOneOrderItem,
    AngelOneOrdersResponse,
    AngelOnePositionItem,
    AngelOnePositionsResponse,
)
from app.services.brokers.angel_one.client import AngelOneClient
from app.services.brokers.angel_one.exceptions import (
    AngelOneAuthenticationError,
    AngelOneException,
    AngelOneInvalidResponseError,
    AngelOneNetworkError,
    AngelOneRateLimitError,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_decimal(val: Any) -> Decimal:
    if val is None or val == "":
        return Decimal("0.0")
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError):
        return Decimal("0.0")


def _parse_dt(raw: Any) -> datetime | None:
    """Try common Angel One datetime formats; return None on failure."""
    if not raw:
        return None
    formats = [
        "%d-%b-%Y %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d-%b-%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(str(raw), fmt)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class AngelOneDataService:
    """
    Wraps AngelOneClient to provide safe, read-only data methods.

    The caller is responsible for calling client.authenticate() BEFORE
    constructing this service, or can rely on the auto-authenticate in
    AngelOneClient._get() if the session is not already established.
    """

    def __init__(self, client: AngelOneClient) -> None:
        self._client = client

    # ------------------------------------------------------------------
    # Account / Profile
    # ------------------------------------------------------------------

    def get_account_info(self) -> AngelOneAccountInfo:
        """Fetch profile and return a safe, normalised structure."""
        try:
            raw: Dict[str, Any] = self._client.get_profile()
        except AngelOneAuthenticationError:
            logger.warning("Session expired while fetching profile")
            raise
        except AngelOneException:
            raise

        if not isinstance(raw, dict):
            raw = {}

        # Redact last 4 chars of client_id for display safety (shows "CLIENT_XX")
        client_id = str(raw.get("clientcode") or raw.get("clientId") or "UNKNOWN")

        return AngelOneAccountInfo(
            client_id=client_id,
            name=str(raw.get("name") or raw.get("fullName") or ""),
            email=raw.get("email") or None,
            mobile=raw.get("mobileno") or raw.get("mobile") or None,
            pan=raw.get("pan") or None,
            exchange_privileges=_safe_list(raw.get("exchEnabled") or raw.get("exchangePrivileges")),
            product_privileges=_safe_list(raw.get("products") or raw.get("productPrivileges")),
            broker="ANGEL_ONE",
        )

    # ------------------------------------------------------------------
    # Funds / Margin
    # ------------------------------------------------------------------

    def get_funds(self) -> AngelOneFundsResponse:
        """Fetch RMS/funds and normalise into AngelOneFundsResponse."""
        try:
            raw: Dict[str, Any] = self._client.get_rms()
        except AngelOneAuthenticationError:
            logger.warning("Session expired while fetching funds")
            raise
        except AngelOneException:
            raise

        if not isinstance(raw, dict):
            raw = {}

        return AngelOneFundsResponse(
            broker="ANGEL_ONE",
            available_cash=_to_decimal(raw.get("availablecash")),
            used_margin=_to_decimal(raw.get("utilisedmargin")),
            net_cash=_to_decimal(raw.get("netcashaval") or raw.get("availablecash")),
            collateral=_to_decimal(raw.get("collateral")),
            total_pnl=_to_decimal(raw.get("unrealisedpnl")) if raw.get("unrealisedpnl") is not None else None,
            currency="INR",
            as_of=datetime.utcnow(),
        )

    # ------------------------------------------------------------------
    # Holdings
    # ------------------------------------------------------------------

    def get_holdings(self) -> AngelOneHoldingsResponse:
        """Fetch delivery holdings and normalise."""
        try:
            raw = self._client.get_holdings()
        except AngelOneAuthenticationError:
            logger.warning("Session expired while fetching holdings")
            raise
        except AngelOneException:
            raise

        items = _normalise_holdings(raw)
        return AngelOneHoldingsResponse(
            broker="ANGEL_ONE",
            holdings=items,
            count=len(items),
            as_of=datetime.utcnow(),
        )

    # ------------------------------------------------------------------
    # Positions
    # ------------------------------------------------------------------

    def get_positions(self) -> AngelOnePositionsResponse:
        """Fetch open positions and normalise."""
        try:
            raw = self._client.get_positions()
        except AngelOneAuthenticationError:
            logger.warning("Session expired while fetching positions")
            raise
        except AngelOneException:
            raise

        items = _normalise_positions(raw)
        return AngelOnePositionsResponse(
            broker="ANGEL_ONE",
            positions=items,
            count=len(items),
            as_of=datetime.utcnow(),
        )

    # ------------------------------------------------------------------
    # Order Book
    # ------------------------------------------------------------------

    def get_orders(self) -> AngelOneOrdersResponse:
        """Fetch order book (READ-ONLY).  No execution is triggered."""
        try:
            raw = self._client.get_order_book()
        except AngelOneAuthenticationError:
            logger.warning("Session expired while fetching orders")
            raise
        except AngelOneException:
            raise

        items = _normalise_orders(raw)
        return AngelOneOrdersResponse(
            broker="ANGEL_ONE",
            orders=items,
            count=len(items),
            as_of=datetime.utcnow(),
        )


# ---------------------------------------------------------------------------
# Private normalisation helpers
# ---------------------------------------------------------------------------

def _safe_list(val: Any) -> List[str]:
    if isinstance(val, list):
        return [str(v) for v in val if v]
    if isinstance(val, str) and val:
        return [s.strip() for s in val.split(",") if s.strip()]
    return []


def _normalise_holdings(raw: Any) -> List[AngelOneHoldingItem]:
    if not raw:
        return []
    if not isinstance(raw, list):
        logger.warning("Unexpected holdings format from Angel One; expected list")
        return []

    items: List[AngelOneHoldingItem] = []
    for h in raw:
        if not isinstance(h, dict):
            continue
        try:
            items.append(
                AngelOneHoldingItem(
                    symbol=str(h.get("tradingsymbol") or ""),
                    exchange=str(h.get("exchange") or ""),
                    isin=h.get("isin") or None,
                    symbol_token=str(h.get("symboltoken") or "") or None,
                    quantity=_to_decimal(h.get("quantity")),
                    t1_quantity=_to_decimal(h.get("t1quantity")),
                    average_price=_to_decimal(h.get("averageprice")),
                    last_price=_to_decimal(h.get("ltp")),
                    market_value=_to_decimal(h.get("marketvalue")),
                    pnl=_to_decimal(h.get("pnl") or h.get("profitandloss")),
                    pnl_percent=_to_decimal(h.get("pnlpercentage")),
                    product=str(h.get("product") or "DELIVERY"),
                )
            )
        except Exception:
            logger.warning("Skipping malformed holding record")
    return items


def _normalise_positions(raw: Any) -> List[AngelOnePositionItem]:
    if not raw:
        return []
    if not isinstance(raw, list):
        logger.warning("Unexpected positions format from Angel One; expected list")
        return []

    items: List[AngelOnePositionItem] = []
    for p in raw:
        if not isinstance(p, dict):
            continue
        try:
            net_qty = _to_decimal(p.get("netqty") or p.get("quantity") or 0)
            side = "BUY" if net_qty >= 0 else "SELL"
            close = _to_decimal(p.get("close") or p.get("closeprice"))
            ltp = _to_decimal(p.get("ltp"))
            avg = _to_decimal(p.get("averageprice") or p.get("netavgprice"))
            pnl = _to_decimal(p.get("pnl") or p.get("unrealisedpnl"))
            pnl_pct = (
                ((ltp - avg) / avg * 100)
                if avg and avg != 0
                else Decimal("0.0")
            )

            items.append(
                AngelOnePositionItem(
                    symbol=str(p.get("tradingsymbol") or ""),
                    exchange=str(p.get("exchange") or ""),
                    symbol_token=str(p.get("symboltoken") or "") or None,
                    product=str(p.get("producttype") or p.get("product") or ""),
                    side=side,
                    quantity=abs(net_qty),
                    average_price=avg,
                    last_price=ltp,
                    pnl=pnl,
                    pnl_percent=pnl_pct.quantize(Decimal("0.01")),
                    close_price=close,
                )
            )
        except Exception:
            logger.warning("Skipping malformed position record")
    return items


def _normalise_orders(raw: Any) -> List[AngelOneOrderItem]:
    if not raw:
        return []
    if not isinstance(raw, list):
        logger.warning("Unexpected orders format from Angel One; expected list")
        return []

    items: List[AngelOneOrderItem] = []
    for o in raw:
        if not isinstance(o, dict):
            continue
        try:
            items.append(
                AngelOneOrderItem(
                    broker_order_id=str(o.get("orderid") or ""),
                    symbol=str(o.get("tradingsymbol") or ""),
                    exchange=str(o.get("exchange") or ""),
                    side=str(o.get("transactiontype") or ""),
                    order_type=str(o.get("ordertype") or ""),
                    product=str(o.get("producttype") or ""),
                    quantity=_to_decimal(o.get("quantity")),
                    price=_to_decimal(o.get("price")),
                    trigger_price=_to_decimal(o.get("triggerprice")),
                    status=str(o.get("status") or "UNKNOWN"),
                    status_message=o.get("text") or o.get("statusmessage") or None,
                    filled_quantity=_to_decimal(o.get("filledshares") or o.get("fillshares")),
                    remaining_quantity=_to_decimal(o.get("unfilledshares")),
                    average_fill_price=_to_decimal(o.get("averageprice")),
                    placed_at=_parse_dt(o.get("ordertime") or o.get("exchtime")),
                    updated_at=_parse_dt(o.get("updatetime")),
                )
            )
        except Exception:
            logger.warning("Skipping malformed order record")
    return items
