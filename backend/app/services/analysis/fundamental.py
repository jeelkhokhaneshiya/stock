from typing import Dict, Any, Tuple, List

class FundamentalAnalyzer:
    def analyze(self, asset_type: str, data: Dict[str, Any]) -> Tuple[float, Dict[str, Any], List[str]]:
        if asset_type != "STOCK":
            return 70.0, {"notes": "Basic check for non-stock"}, []
            
        details = {}
        missing = []
        score = 0.0
        
        revenue_growth = data.get("revenue_growth")
        if revenue_growth is not None:
            details["revenue_growth"] = revenue_growth
            if revenue_growth > 0.10: score += 20
            elif revenue_growth > 0: score += 10
        else:
            missing.append("revenue_growth")
            
        eps_growth = data.get("eps_growth")
        if eps_growth is not None:
            details["eps_growth"] = eps_growth
            if eps_growth > 0.10: score += 20
            elif eps_growth > 0: score += 10
        else:
            missing.append("eps_growth")
            
        roe = data.get("roe")
        if roe is not None:
            details["roe"] = roe
            if roe > 0.15: score += 20
            elif roe > 0.10: score += 10
        else:
            missing.append("roe")
            
        debt_to_equity = data.get("debt_to_equity")
        if debt_to_equity is not None:
            details["debt_to_equity"] = debt_to_equity
            if debt_to_equity < 1.0: score += 20
            elif debt_to_equity < 2.0: score += 10
        else:
            missing.append("debt_to_equity")
            
        fcf = data.get("free_cash_flow")
        if fcf is not None:
            details["free_cash_flow"] = fcf
            if fcf > 0: score += 20
        else:
            missing.append("free_cash_flow")
            
        # Max score here is 100
        return min(100.0, score), details, missing
