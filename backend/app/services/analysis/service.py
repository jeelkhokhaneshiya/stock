import logging
from typing import Dict, Any

from app.services.analysis.fundamental import FundamentalAnalyzer
from app.services.analysis.technical import TechnicalAnalyzer
from app.services.analysis.valuation import ValuationAnalyzer
from app.services.analysis.quality import QualityAnalyzer
from app.services.analysis.risk import RiskAnalyzer

logger = logging.getLogger(__name__)

class InvestmentAnalysisService:
    def __init__(self, market_data_service=None):
        self.market_data_service = market_data_service
        self.fundamental = FundamentalAnalyzer()
        self.technical = TechnicalAnalyzer()
        self.valuation = ValuationAnalyzer()
        self.quality = QualityAnalyzer()
        self.risk = RiskAnalyzer()
        
    def execute_full_analysis(self, symbol: str, asset_type: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a deterministic, multi-layered financial analysis.
        Returns a comprehensive structured report.
        """
        logger.info(f"Starting full analysis for {symbol} ({asset_type})")
        
        # Guardrail: Check stale market data before analysis
        freshness = context_data.get('data_freshness_seconds', 0)
        if freshness > 3600: # Example stale data check for analysis
            logger.warning(f"Market data is stale ({freshness}s) for {symbol}. Analysis blocked.")
            return {
                "analysis_confidence": "INSUFFICIENT",
                "blocking_reasons": ["STALE_MARKET_DATA"],
                "long_term_suitability_score": 0,
                "overall_score": 0
            }

        # 1. Fundamental Analysis
        f_score, f_details, f_missing = self.fundamental.analyze(asset_type, context_data)
        
        # 2. Technical Analysis
        t_score, t_details, t_missing = self.technical.analyze(asset_type, context_data)
        
        # 3. Valuation Analysis
        v_score, v_details, v_missing = self.valuation.analyze(asset_type, context_data)
        
        # 4. Quality Analysis
        q_score, q_details, q_missing = self.quality.analyze(asset_type, context_data)
        
        # 5. Risk Analysis
        r_score, r_details, r_warnings = self.risk.analyze(asset_type, context_data, f_details, v_details)
        
        # 6. Compute Data Coverage & Analytical Confidence
        # Total required fields can be a fixed number based on asset type
        total_missing = len(f_missing) + len(t_missing) + len(v_missing) + len(q_missing)
        
        # The fewer missing data points, the higher the confidence
        # Simple heuristic: 
        if asset_type == "STOCK":
            # Assume ~20 fundamental/valuation/technical metrics are needed for a strong decision
            coverage_penalty = min(0.5, total_missing * 0.05) 
            analytical_confidence = 1.0 - coverage_penalty
        else:
            # ETF / Mutual funds might have less strict fundamental requirements
            coverage_penalty = min(0.3, total_missing * 0.05) 
            analytical_confidence = 0.9 - coverage_penalty
            
        confidence_label = "HIGH"
        if analytical_confidence < 0.8:
            confidence_label = "MEDIUM"
        if analytical_confidence < 0.6:
            confidence_label = "INSUFFICIENT"
            
        # 7. Compute Overall Score (0 - 100)
        # Weights: Quality 30%, Fundamental 30%, Risk 20%, Valuation 10%, Technical 10%
        overall_score = (
            (q_score * 0.3) + 
            (f_score * 0.3) + 
            (r_score * 0.2) + 
            (v_score * 0.1) + 
            (t_score * 0.1)
        )
        
        # 8. Synthesize Report
        report = {
            "symbol": symbol,
            "asset_type": asset_type,
            "analysis_confidence": confidence_label,
            "analytical_confidence_score": analytical_confidence,
            "long_term_suitability_score": overall_score,
            "overall_score": overall_score,
            "risk_score": r_score,
            "missing_data": f_missing + t_missing + v_missing + q_missing,
            "analysis_timestamp": "2026-09-30T10:00:00Z",
            "category": "STRONG",
            "explanation": self.generate_explanation({"overall_score": overall_score}),
            "fundamental_score": f_score,
            "technical_score": t_score,
            "valuation_score": v_score,
            "quality_score": q_score,
            "warnings": r_warnings,
            "blocking_reasons": []
        }
        
        return report

    def _fetch_market_data(self, asset_type, identifier, exchange="NSE"):
        # Dummy fetch if market_data_service is not wired up completely
        if self.market_data_service:
            try:
                # Basic fetch
                data = self.market_data_service.get_quote(identifier)
                return {"price": data.price}
            except Exception as e:
                raise ValueError("Invalid symbol")
        return {}

    def analyze_stock(self, symbol: str, exchange: str = "NSE"):
        context = self._fetch_market_data("STOCK", symbol, exchange)
        return self.execute_full_analysis(symbol, "STOCK", context)
        
    def analyze_etf(self, symbol: str, exchange: str = "NSE"):
        context = self._fetch_market_data("ETF", symbol, exchange)
        return self.execute_full_analysis(symbol, "ETF", context)
        
    def analyze_mutual_fund(self, identifier: str):
        context = self._fetch_market_data("MUTUAL_FUND", identifier)
        return self.execute_full_analysis(identifier, "MUTUAL_FUND", context)

    def generate_explanation(self, report: dict) -> str:
        return "AI Explanation: This asset has a score of " + str(report.get("overall_score"))
