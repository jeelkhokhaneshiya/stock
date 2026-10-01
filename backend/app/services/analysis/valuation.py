from typing import Dict, Any, Tuple, List

class ValuationAnalyzer:
    def analyze(self, asset_type: str, data: Dict[str, Any]) -> Tuple[float, Dict[str, Any], List[str]]:
        if asset_type != "STOCK":
            return 50.0, {}, []
            
        details = {}
        missing = []
        score = 50.0 # neutral base
        
        pe_ratio = data.get("pe_ratio")
        if pe_ratio is not None:
            details["pe_ratio"] = pe_ratio
            if pe_ratio < 15: score += 20
            elif pe_ratio > 35: score -= 10 # penalty, but don't strictly reject just for PE
        else:
            missing.append("pe_ratio")
            
        pb_ratio = data.get("pb_ratio")
        if pb_ratio is not None:
            details["pb_ratio"] = pb_ratio
            if pb_ratio < 2: score += 20
            elif pb_ratio > 5: score -= 10
        else:
            missing.append("pb_ratio")
            
        return max(0.0, min(100.0, score)), details, missing
