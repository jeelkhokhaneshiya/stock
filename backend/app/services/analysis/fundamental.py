from typing import Dict, Any, Tuple, List
from datetime import datetime, timezone

class FundamentalAnalyzer:
    def analyze(self, asset_type: str, data: Dict[str, Any]) -> Tuple[float, Dict[str, Any], List[str]]:
        if asset_type != "STOCK":
            return 50.0, {"notes": "Basic check for non-stock"}, []
            
        details = {}
        missing = []
        score = 0.0
        max_score = 0.0
        
        # Revenue Growth
        revenue_growth = data.get("revenue_growth")
        if revenue_growth is not None:
            max_score += 20
            details["revenue_growth"] = {"value": revenue_growth, "status": "AVAILABLE"}
            if revenue_growth > 0.10: score += 20
            elif revenue_growth > 0: score += 10
        else:
            details["revenue_growth"] = {"value": None, "status": "UNAVAILABLE"}
            missing.append("revenue_growth")
            
        # EPS Growth
        eps_growth = data.get("eps_growth")
        if eps_growth is not None:
            max_score += 20
            details["eps_growth"] = {"value": eps_growth, "status": "AVAILABLE"}
            if eps_growth > 0.10: score += 20
            elif eps_growth > 0: score += 10
        else:
            details["eps_growth"] = {"value": None, "status": "UNAVAILABLE"}
            missing.append("eps_growth")
            
        # ROE
        roe = data.get("roe")
        if roe is not None:
            max_score += 20
            details["roe"] = {"value": roe, "status": "AVAILABLE"}
            if roe > 0.15: score += 20
            elif roe > 0.10: score += 10
        else:
            details["roe"] = {"value": None, "status": "UNAVAILABLE"}
            missing.append("roe")
            
        # Debt to Equity
        debt_to_equity = data.get("debt_to_equity")
        if debt_to_equity is not None:
            max_score += 20
            details["debt_to_equity"] = {"value": debt_to_equity, "status": "AVAILABLE"}
            if debt_to_equity < 1.0: score += 20
            elif debt_to_equity < 2.0: score += 10
        else:
            details["debt_to_equity"] = {"value": None, "status": "UNAVAILABLE"}
            missing.append("debt_to_equity")
            
        # Free Cash Flow
        fcf = data.get("free_cash_flow")
        if fcf is not None:
            max_score += 20
            details["free_cash_flow"] = {"value": fcf, "status": "AVAILABLE"}
            if fcf > 0: score += 20
        else:
            details["free_cash_flow"] = {"value": None, "status": "UNAVAILABLE"}
            missing.append("free_cash_flow")
            
        # P/E Ratio
        pe_ratio = data.get("pe_ratio")
        if pe_ratio is not None:
            max_score += 20
            details["pe_ratio"] = {"value": pe_ratio, "status": "AVAILABLE"}
            if pe_ratio < 20 and pe_ratio > 0: score += 20
            elif pe_ratio < 30 and pe_ratio > 0: score += 10
        else:
            details["pe_ratio"] = {"value": None, "status": "UNAVAILABLE"}
            missing.append("pe_ratio")

        normalized_score = (score / max_score * 100) if max_score > 0 else 50.0
        
        return min(100.0, normalized_score), details, missing

    def analyze_fundamentals(self, symbol: str, fundamental_data: Any) -> Dict[str, Any]:
        """
        Public endpoint to get a fully structured fundamental analysis object.
        fundamental_data could be None if the provider doesn't have it.
        """
        if not fundamental_data:
            return {
                "status": "UNAVAILABLE",
                "fundamental_score": 0.0,
                "metrics": {},
                "warnings": ["Fundamental data unavailable for this symbol"],
                "confidence": 0.0
            }

        data_dict = {}
        if hasattr(fundamental_data, "__dataclass_fields__"):
            from dataclasses import asdict
            data_dict = asdict(fundamental_data)
        elif hasattr(fundamental_data, "dict"):
            data_dict = fundamental_data.dict()
        elif isinstance(fundamental_data, dict):
            data_dict = fundamental_data

        score, details, missing = self.analyze("STOCK", data_dict)
        
        provider_confidence = data_dict.get("confidence", 1.0)
        confidence = (1.0 - (len(missing) / max(1, len(details)))) * provider_confidence
        
        return {
            "status": "SUCCESS",
            "fundamental_score": score,
            "metrics": details,
            "missing_metrics": missing,
            "warnings": [f"Missing data for: {', '.join(missing)}"] if missing else [],
            "confidence": confidence
        }
