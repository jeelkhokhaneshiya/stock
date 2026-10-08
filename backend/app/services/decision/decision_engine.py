from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone

class DecisionEngine:
    def _evaluate_thesis(self, analysis: Dict[str, Any]) -> str:
        f_score = analysis.get("fundamental_score", 50)
        t_score = analysis.get("technical_score", 50)
        r_score = analysis.get("risk_score", 50)
        confidence = analysis.get("confidence", 0)
        freshness = analysis.get("data_freshness", "STALE")
        
        if freshness == "STALE" or confidence < 0.3:
            return "INSUFFICIENT_DATA"
            
        if f_score >= 70 and t_score >= 60 and r_score >= 60:
            return "THESIS_STRONG"
        if f_score >= 50 and t_score >= 40:
            return "THESIS_STABLE"
        if f_score < 35 and t_score < 30:
            return "THESIS_BROKEN"
        if f_score < 45 and t_score < 40:
            return "THESIS_WEAK"
        
        return "THESIS_UNCERTAIN"

    def evaluate_holding(self, holding: Dict[str, Any], analysis: Dict[str, Any], portfolio_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        SELL / HOLD DECISION ENGINE with LOSS-AWARE Logic
        """
        symbol = holding.get("symbol")
        pnl_pct = holding.get("pnl_percentage", 0)
        overall_score = analysis.get("overall_score", 50)
        freshness = analysis.get("data_freshness", "STALE")
        valuation_score = analysis.get("valuation_score", 50)
        r_score = analysis.get("risk_score", 50)
        
        allocations = portfolio_context.get("concentration", {}).get("asset_allocation", [])
        current_alloc_pct = next((a["percentage"] for a in allocations if a["symbol"] == symbol), 0)
        
        thesis_status = self._evaluate_thesis(analysis)
        current_qty = holding.get("quantity", 0)
        current_price = holding.get("ltp", 0)
        
        # Determine normalized action and reasoning
        action = "HOLD"
        suggested_qty = 0
        reasons = []
        
        is_loss = pnl_pct < 0
        
        if thesis_status == "INSUFFICIENT_DATA":
            action = "WATCH" if current_qty == 0 else "NO_ACTION"
            reasons.append("Insufficient or stale data to form a confident decision.")
            if is_loss:
                reasons.append("Position is in loss, but missing data prevents SELL recommendation.")
        
        elif is_loss:
            if thesis_status == "THESIS_STRONG":
                if valuation_score > 60 and r_score > 50 and current_alloc_pct < 10:
                    action = "BUY_MORE"
                    reasons.append("Thesis is STRONG and valuation is attractive. Safe to average down.")
                else:
                    action = "HOLD"
                    reasons.append("Thesis is STRONG. Do not sell despite the loss.")
            elif thesis_status == "THESIS_STABLE":
                action = "HOLD"
                reasons.append("Thesis is STABLE. Hold through current weakness.")
            elif thesis_status == "THESIS_UNCERTAIN":
                action = "HOLD"
                reasons.append("Thesis is UNCERTAIN. Monitor closely.")
            elif thesis_status == "THESIS_WEAK":
                action = "REDUCE"
                reasons.append("Thesis is WEAK and position is losing. Reduction recommended.")
            elif thesis_status == "THESIS_BROKEN":
                action = "SELL"
                reasons.append("Thesis is BROKEN and position is losing. Stop-loss/exit recommended.")
                
        else: # PROFIT
            if current_alloc_pct > 30:
                action = "REDUCE"
                reasons.append(f"High portfolio concentration ({current_alloc_pct:.1f}%). Rebalancing recommended to lock in profits.")
            elif valuation_score < 30:
                action = "REDUCE"
                reasons.append("Valuation is extremely stretched. Consider taking some profits.")
            elif thesis_status == "THESIS_BROKEN":
                action = "SELL"
                reasons.append("Thesis is BROKEN despite being in profit. Exit recommended.")
            elif thesis_status == "THESIS_STRONG":
                if valuation_score > 60 and r_score > 50 and current_alloc_pct < 10:
                    action = "BUY_MORE"
                    reasons.append("Thesis is STRONG, valuation is good, and allocation is low. Can add to winners.")
                else:
                    action = "HOLD"
                    reasons.append("Thesis is STRONG. Let profits run.")
            else:
                action = "HOLD"
                reasons.append(f"Thesis is {thesis_status}. Hold the profitable position.")
                
        return {
            "symbol": symbol,
            "company_name": holding.get("company_name", symbol),
            "action": action,
            "decision": action, # Kept for backward compatibility
            "quantity": suggested_qty, # Will be filled by PortfolioManager using PositionSizer
            "current_quantity": current_qty,
            "recommended_quantity_after_action": current_qty, # Will be updated
            "current_price": current_price,
            "estimated_value": 0.0,
            "confidence": analysis.get("confidence", 0),
            "thesis_status": thesis_status,
            "data_freshness": freshness,
            "pnl_pct": pnl_pct,
            "risk_score": r_score,
            "portfolio_allocation": current_alloc_pct,
            "reasons": reasons,
            "risks": analysis.get("warnings", []),
            "missing_data": analysis.get("missing_data", []),
            "analysis_timestamp": datetime.now(timezone.utc).isoformat()
        }
