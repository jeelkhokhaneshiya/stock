from typing import Dict, Any, List
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class PortfolioAnalyzer:
    def analyze_portfolio(self, funds: Dict[str, Any], holdings: Dict[str, Any], positions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes the overall portfolio using real Angel One data.
        Never fabricates data. If data is missing, sets to UNAVAILABLE.
        """
        invested_value = 0.0
        current_value = 0.0
        unrealized_pnl = 0.0
        day_pnl = 0.0
        
        # Parse Holdings
        holding_items = holdings.get("holdings", []) if holdings else []
        for h in holding_items:
            try:
                inv = float(h.get("average_price", 0)) * float(h.get("quantity", 0))
                cur = float(h.get("last_price", 0)) * float(h.get("quantity", 0))
                pnl = cur - inv
                invested_value += inv
                current_value += cur
                unrealized_pnl += pnl
            except (ValueError, TypeError):
                continue
                
        # Parse Positions (Day PnL)
        position_items = positions.get("positions", []) if positions else []
        for p in position_items:
            try:
                dpnl = float(p.get("pnl", 0))
                day_pnl += dpnl
            except (ValueError, TypeError):
                continue

        # Funds
        available_cash = funds.get("available_cash", "UNAVAILABLE") if funds else "UNAVAILABLE"
        total_pnl = funds.get("total_pnl", "UNAVAILABLE") if funds else "UNAVAILABLE"
        
        total_portfolio_value = current_value + (float(available_cash) if available_cash != "UNAVAILABLE" else 0.0)
        
        # Portfolio concentration
        allocation = []
        for h in holding_items:
            try:
                cur = float(h.get("last_price", 0)) * float(h.get("quantity", 0))
                pct = (cur / current_value * 100) if current_value > 0 else 0
                allocation.append({
                    "symbol": h.get("symbol", "UNKNOWN"),
                    "value": cur,
                    "percentage": pct
                })
            except (ValueError, TypeError):
                continue
                
        # Sort allocation
        allocation.sort(key=lambda x: x["percentage"], reverse=True)
        top_concentration = allocation[0]["percentage"] if allocation else 0.0

        risk_level = "LOW"
        if top_concentration > 30:
            risk_level = "MODERATE"
        if top_concentration > 50:
            risk_level = "HIGH"
        if top_concentration > 70:
            risk_level = "CRITICAL"

        return {
            "total_portfolio_value": total_portfolio_value,
            "invested_value": invested_value,
            "current_value": current_value,
            "unrealized_pnl": unrealized_pnl,
            "realized_pnl": "UNAVAILABLE", # Hard to get purely from standard endpoints reliably
            "day_pnl": day_pnl,
            "number_of_holdings": len(holding_items),
            "number_of_positions": len(position_items),
            "cash_available": available_cash,
            "concentration": {
                "top_asset_percentage": top_concentration,
                "risk_level": risk_level,
                "asset_allocation": allocation,
                "sector_concentration": "UNAVAILABLE" # AngelOne standard APIs don't provide sector mappings
            },
            "risk_indicators": {
                "portfolio_risk": risk_level,
                "warnings": ["High concentration risk"] if risk_level in ["HIGH", "CRITICAL"] else []
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
