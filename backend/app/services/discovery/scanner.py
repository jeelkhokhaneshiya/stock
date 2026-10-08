import logging
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class MarketScanner:
    """
    Automatic Market Discovery Pipeline.
    Fetches the entire NSE/BSE universe from Angel One, filters for valid/liquid
    instruments, and ranks them for analysis.
    """
    INSTRUMENT_LIST_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

    def __init__(self):
        self.http_client = httpx.Client(timeout=30.0)

    def __del__(self):
        try:
            self.http_client.close()
        except:
            pass

    def fetch_master_universe(self) -> List[Dict[str, Any]]:
        """Fetches the complete supported stock universe from Angel One."""
        try:
            logger.info("Fetching Angel One master instrument universe...")
            response = self.http_client.get(self.INSTRUMENT_LIST_URL)
            response.raise_for_status()
            data = response.json()
            logger.info("Fetched %d instruments from master list.", len(data))
            return data
        except Exception as e:
            logger.error("Failed to fetch master universe: %s", str(e))
            return []

    def filter_eligible_candidates(self, master_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filters the raw universe for eligible investment candidates.
        - Must be NSE Equity (exch_seg == 'NSE' and instrumenttype == '')
        - Remove indices, options, futures.
        """
        eligible = []
        for item in master_list:
            exch_seg = item.get("exch_seg")
            symbol = item.get("symbol", "")
            
            # Basic filtering for NSE equity stocks
            if exch_seg == "NSE" and "-EQ" in symbol:
                eligible.append(item)

        logger.info("Filtered down to %d eligible candidates.", len(eligible))
        return eligible

    def discover_opportunities(self) -> Dict[str, Any]:
        """
        Runs the full discovery pipeline.
        Returns the top candidates ready for fundamental/technical analysis.
        """
        master_list = self.fetch_master_universe()
        if not master_list:
            return {"error": "Failed to fetch universe", "candidates": []}

        candidates = self.filter_eligible_candidates(master_list)
        
        # We will sort or sample the candidates based on deterministic rules
        # For now, return a safe subset to prevent overloading the system
        top_candidates = candidates[:50] # Placeholder for advanced ranking

        return {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "source": "Angel One OpenAPIScripMaster",
            "total_discovered": len(candidates),
            "candidates": top_candidates
        }
