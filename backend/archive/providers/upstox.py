import logging
import httpx
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from app.core.config import settings

logger = logging.getLogger(__name__)

class UpstoxFundamentalDataProvider:
    def __init__(self):
        self.api_key = settings.MARKET_DATA_API_KEY
        self.base_url = "https://api.upstox.com/v2/fundamentals"
        
    def _fetch_endpoint(self, isin: str, endpoint: str) -> Optional[Dict[str, Any]]:
        if not self.api_key or self.api_key == "placeholder":
            logger.warning("Upstox Fundamental API key not configured.")
            return None
            
        url = f"{self.base_url}/{isin}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    return data.get("data", {})
                else:
                    logger.warning(f"Upstox API returned {res.status_code} for {url}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching Upstox fundamentals for {isin} ({endpoint}): {str(e)}")
            return None

    def get_fundamentals(self, symbol: str, exchange: str, isin: Optional[str] = None) -> Any:
        if not isin:
            logger.warning(f"ISIN not provided for {symbol}. Upstox API requires ISIN.")
            return None
            
        # We need to fetch from multiple endpoints to build the fundamental data object
        # 1. Income Statement
        income = self._fetch_endpoint(isin, "income-statement") or {}
        # 2. Key Ratios
        ratios = self._fetch_endpoint(isin, "key-ratios") or {}
        # 3. Balance Sheet
        balance = self._fetch_endpoint(isin, "balance-sheet") or {}
        
        # Parse data out
        # Note: Upstox typically returns lists of historical periods, we take the most recent
        
        def _get_latest(data_dict: Dict[str, Any], key: str) -> Optional[float]:
            # This is a safe fallback to extract latest metric if Upstox returns lists
            if not data_dict: return None
            # Check if it's directly there
            if key in data_dict:
                try: return float(data_dict[key])
                except: pass
            # Check if it's a list (e.g. historical periods)
            if isinstance(data_dict, list) and len(data_dict) > 0:
                first = data_dict[0]
                if isinstance(first, dict) and key in first:
                    try: return float(first[key])
                    except: pass
            return None

        # Build our expected dictionary structure
        result = {}
        
        # Revenue
        rev = _get_latest(income, "revenue") or _get_latest(income, "total_revenue")
        if rev is not None: result["revenue"] = rev
        
        # Revenue Growth
        rev_growth = _get_latest(income, "revenue_growth") or _get_latest(ratios, "revenue_growth")
        if rev_growth is not None: result["revenue_growth"] = rev_growth
        
        # Operating Profit
        op = _get_latest(income, "operating_profit")
        if op is not None: result["operating_profit"] = op
        
        # Net Profit
        np = _get_latest(income, "net_income") or _get_latest(income, "net_profit")
        if np is not None: result["net_profit"] = np
        
        # Profit Growth
        pg = _get_latest(income, "net_income_growth") or _get_latest(ratios, "profit_growth")
        if pg is not None: result["profit_growth"] = pg
        
        # EPS
        eps = _get_latest(income, "eps") or _get_latest(ratios, "eps")
        if eps is not None: result["eps"] = eps
        
        # EPS Growth
        eps_g = _get_latest(income, "eps_growth") or _get_latest(ratios, "eps_growth")
        if eps_g is not None: result["eps_growth"] = eps_g
        
        # ROE
        roe = _get_latest(ratios, "roe") or _get_latest(ratios, "return_on_equity")
        if roe is not None: result["roe"] = roe
        
        # ROCE
        roce = _get_latest(ratios, "roce") or _get_latest(ratios, "return_on_capital_employed")
        if roce is not None: result["roce"] = roce
        
        # Debt to Equity
        dte = _get_latest(ratios, "debt_to_equity") or _get_latest(balance, "debt_to_equity")
        if dte is not None: result["debt_to_equity"] = dte
        
        # Free Cash Flow
        fcf = _get_latest(ratios, "free_cash_flow") or _get_latest(income, "free_cash_flow")
        if fcf is not None: result["free_cash_flow"] = fcf
        
        # P/E Ratio
        pe = _get_latest(ratios, "pe_ratio") or _get_latest(ratios, "pe")
        if pe is not None: result["pe_ratio"] = pe
        
        # Book Value
        bv = _get_latest(ratios, "book_value") or _get_latest(balance, "book_value")
        if bv is not None: result["book_value"] = bv
        
        if not result:
            return None
            
        result["data_source"] = "UPSTOX"
        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        return result
