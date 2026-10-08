from typing import Dict, Any, List
from datetime import datetime, timezone
from app.services.market_data.factory import get_market_data_service
from app.services.analysis.technical import TechnicalAnalyzer
from app.services.analysis.fundamental import FundamentalAnalyzer
from app.services.analysis.multi_timeframe import MultiTimeframeAnalyzer
from app.services.analysis.risk import RiskAnalyzer

class HoldingAnalyzer:
    def __init__(self):
        self.market_data_service = get_market_data_service()
        self.technical = TechnicalAnalyzer()
        self.fundamental = FundamentalAnalyzer()
        self.mtf = MultiTimeframeAnalyzer(self.market_data_service)
        self.risk = RiskAnalyzer()

    def analyze_holdings(self, holdings_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        results = []
        holding_items = holdings_data.get("holdings", []) if holdings_data else []
        
        for h in holding_items:
            symbol = h.get("symbol")
            exchange = h.get("exchange", "NSE")
            qty = h.get("quantity", 0)
            avg_price = float(h.get("average_price", 0))
            ltp = float(h.get("last_price", 0))
            qty = float(h.get("quantity", 0))
            
            invested_value = avg_price * qty
            current_value = ltp * qty
            pnl = current_value - invested_value
            pnl_pct = (pnl / invested_value * 100.0) if invested_value > 0 else 0.0
            
            isin = h.get("isin", "")
            
            # Fetch Market Data
            mtf_res = self.mtf.analyze(symbol, exchange)
            try:
                fund_data = self.market_data_service.get_fundamentals(symbol, exchange, isin=isin)
            except NotImplementedError:
                fund_data = None
            
            fund_res = self.fundamental.analyze_fundamentals(symbol, fund_data)
            
            # Extract scores
            t_score = mtf_res.get("summary", {}).get("multi_timeframe_score", 50.0)
            f_score = fund_res.get("fundamental_score", 50.0)
            
            # Risk Evaluation
            r_score, r_details, r_warnings = self.risk.analyze(
                "STOCK", 
                {"volatility": mtf_res.get("timeframes", {}).get("Daily", {}).get("volatility")},
                fund_res.get("metrics", {}),
                {}
            )
            
            overall_score = (t_score * 0.4) + (f_score * 0.4) + (r_score * 0.2)
            
            # Rough Decision Logic (will be refined by Decision Engine)
            decision = "HOLD"
            if overall_score > 75: decision = "BUY"
            elif overall_score < 40: decision = "SELL"
            
            freshness = mtf_res.get("timeframes", {}).get("Daily", {}).get("freshness", "STALE")
            
            results.append({
                "symbol": symbol,
                "exchange": exchange,
                "quantity": qty,
                "average_price": avg_price,
                "current_price": ltp,
                "invested_value": invested_value,
                "current_value": current_value,
                "pnl": pnl,
                "pnl_percentage": pnl_pct,
                "analysis": {
                    "technical_score": t_score,
                    "fundamental_score": f_score,
                    "risk_score": r_score,
                    "multi_timeframe_trend": mtf_res.get("summary", {}).get("trend_alignment", "NEUTRAL"),
                    "data_freshness": freshness,
                    "overall_score": overall_score,
                    "confidence": min(mtf_res.get("summary", {}).get("confidence", 0), fund_res.get("confidence", 0)),
                    "warnings": r_warnings,
                    "decision": decision
                }
            })
            
        return results
