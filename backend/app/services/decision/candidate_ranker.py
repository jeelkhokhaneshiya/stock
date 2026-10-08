from typing import Dict, Any, List
from datetime import datetime, timezone
import logging
from app.services.market_data.factory import get_market_data_service
from app.services.analysis.technical import TechnicalAnalyzer
from app.services.analysis.fundamental import FundamentalAnalyzer
from app.services.analysis.multi_timeframe import MultiTimeframeAnalyzer
from app.services.analysis.risk import RiskAnalyzer
from app.services.discovery.scanner import MarketScanner

logger = logging.getLogger(__name__)

class CandidateRanker:
    def __init__(self):
        self.market_data_service = get_market_data_service()
        self.technical = TechnicalAnalyzer()
        self.fundamental = FundamentalAnalyzer()
        self.mtf = MultiTimeframeAnalyzer(self.market_data_service)
        self.risk = RiskAnalyzer()
        self.scanner = MarketScanner()

    def _evaluate_candidate_thesis(self, f_score: float, t_score: float, r_score: float, v_score: float) -> str:
        if f_score >= 60 and t_score >= 60 and r_score >= 60 and v_score >= 50:
            return "THESIS_STRONG"
        if f_score >= 50 and t_score >= 40:
            return "THESIS_STABLE"
        if f_score < 40 and t_score < 40:
            return "THESIS_WEAK"
        return "THESIS_UNCERTAIN"

    def discover_and_rank(self, limit: int = 10) -> List[Dict[str, Any]]:
        candidates = []
        
        try:
            # 1. Use Phase 1 Discovery
            discovery_res = self.scanner.discover_opportunities()
            candidates_list = discovery_res.get("candidates", [])
            discovered_symbols = [c.get("symbol") for c in candidates_list if c.get("symbol")]
            # Do not filter -EQ so that symbol matches master token map
            discovered_symbols = [s for s in discovered_symbols]

            for symbol in discovered_symbols[:limit * 3]:
                # 2. Market Data
                mtf_res = self.mtf.analyze(symbol, "NSE")
                try:
                    isin = next((cand.get("isin") for cand in candidates_list if isinstance(cand, dict) and cand.get("symbol") == symbol), None)
                    fund_data = self.market_data_service.get_fundamentals(symbol, "NSE", isin=isin)
                except NotImplementedError:
                    fund_data = None
                    
                fund_res = self.fundamental.analyze_fundamentals(symbol, fund_data)
                
                # 3. Scores
                t_score = mtf_res.get("summary", {}).get("multi_timeframe_score", 50.0)
                f_score = fund_res.get("fundamental_score", 50.0)
                v_score = fund_res.get("valuation_score", 50.0) # Assume fundamental analyzer returns this
                
                # 4. Risk
                r_score, r_details, r_warnings = self.risk.analyze(
                    "STOCK", 
                    {"volatility": mtf_res.get("timeframes", {}).get("Daily", {}).get("volatility")},
                    fund_res.get("metrics", {}),
                    {}
                )
                
                overall_score = (t_score * 0.3) + (f_score * 0.3) + (v_score * 0.2) + (r_score * 0.2)
                confidence = min(mtf_res.get("summary", {}).get("confidence", 0), fund_res.get("confidence", 0))
                freshness = mtf_res.get("timeframes", {}).get("Daily", {}).get("freshness", "STALE")
                
                thesis_status = self._evaluate_candidate_thesis(f_score, t_score, r_score, v_score)
                
                # 5. Buy Candidate Rules
                action = "WATCH"
                reasons = []
                
                if freshness == "STALE" or confidence < 0.4:
                    reasons.append("Data is stale or confidence is too low. Cannot recommend.")
                    action = "NO_ACTION"
                elif r_score < 40:
                    reasons.append("Risk is excessive. Rejected for BUY.")
                    action = "NO_ACTION"
                elif v_score < 30:
                    reasons.append("Valuation is extremely stretched. Rejected for BUY.")
                    action = "NO_ACTION"
                elif thesis_status == "THESIS_WEAK":
                    reasons.append("Long-term thesis is weak based on current metrics.")
                    action = "NO_ACTION"
                elif thesis_status == "THESIS_STRONG" and overall_score > 60:
                    action = "BUY"
                    reasons.append("Strong technical trend, solid fundamentals, and reasonable valuation.")
                elif thesis_status == "THESIS_STABLE":
                    reasons.append("Thesis is stable, but waiting for stronger confirmation before buying.")
                    action = "WATCH"
                else:
                    reasons.append("Metrics do not meet stringent BUY thresholds.")
                    action = "WATCH"
                    
                candidates.append({
                    "symbol": symbol,
                    "company_name": symbol, # Map later if possible
                    "action": action,
                    "decision": action, # Kept for backward compatibility
                    "quantity": 0, # To be filled by PortfolioManager
                    "current_quantity": 0,
                    "recommended_quantity_after_action": 0,
                    "current_price": mtf_res.get("timeframes", {}).get("Daily", {}).get("close", 0.0),
                    "estimated_value": 0.0,
                    "technical_score": t_score,
                    "fundamental_score": f_score,
                    "valuation_score": v_score,
                    "risk_score": r_score,
                    "overall_score": overall_score,
                    "confidence": confidence,
                    "thesis_status": thesis_status,
                    "reasons": reasons,
                    "risks": r_warnings,
                    "warnings": r_warnings, # Backwards compat
                    "data_freshness": freshness,
                    "analysis_timestamp": datetime.now(timezone.utc).isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error ranking candidates: {str(e)}")
            
        # Rank by overall score
        candidates.sort(key=lambda x: x["overall_score"], reverse=True)
        
        # Only return the best limits
        candidates = candidates[:limit]
        
        # Add rank field
        for i, c in enumerate(candidates):
            c["rank"] = i + 1
            
        return candidates
