from typing import Dict, Any

class PositionSizer:
    def suggest_allocation(self, symbol: str, current_price: float, available_funds: float, portfolio_value: float, risk_score: float, current_allocation_pct: float, confidence: float = 1.0, volatility: float = 0.0) -> Dict[str, Any]:
        """
        Calculates suggested position sizing.
        PAPER / DECISION SUPPORT ONLY. Never executes real orders.
        """
        # Maximum allowed allocation for any single stock is 10%
        MAX_ALLOCATION_PCT = 10.0
        
        # Base suggested allocation based on risk score (higher score = safer)
        if risk_score > 80:
            target_pct = 8.0
        elif risk_score > 60:
            target_pct = 5.0
        elif risk_score > 40:
            target_pct = 2.0
        else:
            target_pct = 0.0 # Too risky
            
        # Adjust for confidence
        target_pct *= confidence
        
        # Adjust for volatility (reduce size if highly volatile)
        if volatility > 0.05: # > 5% daily volatility
            target_pct *= 0.5
            
        target_pct = min(target_pct, MAX_ALLOCATION_PCT)
            
        # Check current allocation
        remaining_headroom_pct = target_pct - current_allocation_pct
        
        # Maximum allowed quantity (total we could potentially hold)
        max_allowed_amount = (MAX_ALLOCATION_PCT / 100.0) * portfolio_value
        max_allowed_quantity = int(max_allowed_amount / current_price) if current_price > 0 else 0
        
        if remaining_headroom_pct <= 0:
            return {
                "symbol": symbol,
                "suggested_allocation_percent": 0.0,
                "suggested_amount": 0.0,
                "suggested_quantity": 0,
                "resulting_allocation": current_allocation_pct,
                "max_allowed_quantity": max_allowed_quantity,
                "risk_level": "MODERATE" if risk_score > 40 else "HIGH",
                "sizing_reason": "Current allocation already meets or exceeds target.",
                "notice": "PAPER / DECISION SUPPORT ONLY"
            }
            
        suggested_amount = (remaining_headroom_pct / 100.0) * portfolio_value
        
        # Ensure we don't suggest more than available funds
        if suggested_amount > available_funds:
            suggested_amount = available_funds
            
        suggested_quantity = int(suggested_amount / current_price) if current_price > 0 else 0
        
        # Recalculate amount based on discrete quantity
        suggested_amount = suggested_quantity * current_price
        
        resulting_allocation = current_allocation_pct + ((suggested_amount / portfolio_value * 100.0) if portfolio_value > 0 else 0.0)
        
        return {
            "symbol": symbol,
            "suggested_allocation_percent": round((suggested_amount / portfolio_value * 100.0) if portfolio_value > 0 else 0.0, 2),
            "suggested_amount": round(suggested_amount, 2),
            "suggested_quantity": suggested_quantity,
            "resulting_allocation": round(resulting_allocation, 2),
            "max_allowed_quantity": max_allowed_quantity,
            "risk_level": "LOW" if risk_score > 80 else "MODERATE",
            "sizing_reason": f"Target allocation is {target_pct:.1f}%. Current is {current_allocation_pct:.1f}%. Risk adjusted.",
            "notice": "PAPER / DECISION SUPPORT ONLY"
        }

    def suggest_reduction(self, symbol: str, current_price: float, current_quantity: int, thesis_status: str, portfolio_value: float, current_allocation_pct: float) -> Dict[str, Any]:
        """
        Calculates exact quantity to SELL based on thesis deterioration or concentration.
        """
        if thesis_status in ["THESIS_BROKEN", "INSUFFICIENT_DATA"]:
            # Sell entirely if thesis is broken or insufficient data when a reduction is flagged
            sell_qty = current_quantity
            reason = "Complete exit recommended due to broken thesis or critical data failure."
        elif current_allocation_pct > 15.0:
            # Overconcentrated, trim back to 10%
            target_alloc = 10.0
            excess_pct = current_allocation_pct - target_alloc
            excess_amount = (excess_pct / 100.0) * portfolio_value
            sell_qty = int(excess_amount / current_price) if current_price > 0 else 0
            # Ensure we sell at least 1, but not more than we have
            sell_qty = max(1, min(sell_qty, current_quantity))
            reason = f"Trimming position to respect concentration limits (excess ~{excess_pct:.1f}%)."
        else:
            # Partial reduction for weak thesis (e.g. trim 50%)
            sell_qty = max(1, current_quantity // 2)
            reason = "Partial reduction recommended due to weakening thesis."

        return {
            "symbol": symbol,
            "suggested_sell_quantity": sell_qty,
            "resulting_quantity": current_quantity - sell_qty,
            "reason": reason
        }
