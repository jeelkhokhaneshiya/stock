from typing import Dict, Any, List
from datetime import datetime, timezone
import logging
from app.services.brokers.angel_one.data_service import AngelOneDataService
from app.api.deps import get_angel_one_data_service
from app.services.portfolio.portfolio_analyzer import PortfolioAnalyzer
from app.services.portfolio.holding_analyzer import HoldingAnalyzer
from app.services.decision.decision_engine import DecisionEngine
from app.services.decision.candidate_ranker import CandidateRanker
from app.services.portfolio.position_sizer import PositionSizer
from app.services.portfolio.alert_engine import get_alert_engine

logger = logging.getLogger(__name__)

class PortfolioManager:
    def __init__(self, client: AngelOneDataService = None):
        self.client = client or get_angel_one_data_service()
        self.portfolio_analyzer = PortfolioAnalyzer()
        self.holding_analyzer = HoldingAnalyzer()
        self.decision_engine = DecisionEngine()
        self.candidate_ranker = CandidateRanker()
        self.position_sizer = PositionSizer()
        self.alert_engine = get_alert_engine()

    def _get_disconnected_response(self, reason: str) -> Dict[str, Any]:
        return {
            "status": "BROKER_DISCONNECTED",
            "data_freshness": "UNAVAILABLE",
            "portfolio_summary": {
                "total_portfolio_value": 0,
                "total_pnl": 0,
                "cash_available": "UNAVAILABLE",
                "risk_indicators": {"portfolio_risk_level": "UNKNOWN"}
            },
            "holdings_analysis": [],
            "buy_candidates": [],
            "sell_review": [],
            "watchlist": [],
            "risk_summary": {"portfolio_risk_level": "UNKNOWN"},
            "reason": reason,
            "retryable": True,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    def get_full_portfolio_analysis(self) -> Dict[str, Any]:
        """
        Orchestrates the entire Portfolio Intelligence dashboard data.
        """
        if not self.client:
            self.alert_engine.trigger_alert("BROKER_DISCONNECTED", "Angel One client is not initialized.")
            return self._get_disconnected_response("Broker not initialized")
            
        try:
            # Fetch real data and convert to dicts if they are Pydantic models
            funds_res = self.client.get_funds()
            funds = funds_res.model_dump() if hasattr(funds_res, 'model_dump') else (funds_res.dict() if hasattr(funds_res, 'dict') else funds_res)
            
            holdings_res = self.client.get_holdings()
            holdings = holdings_res.model_dump() if hasattr(holdings_res, 'model_dump') else (holdings_res.dict() if hasattr(holdings_res, 'dict') else holdings_res)
            
            positions_res = self.client.get_positions()
            positions = positions_res.model_dump() if hasattr(positions_res, 'model_dump') else (positions_res.dict() if hasattr(positions_res, 'dict') else positions_res)
            
            # 1. Portfolio Analysis
            portfolio_summary = self.portfolio_analyzer.analyze_portfolio(funds, holdings, positions)
            
            # 2. Holding Analysis
            raw_holdings_analysis = self.holding_analyzer.analyze_holdings(holdings)
            
            # 3. Decision Engine on Holdings
            holdings_analysis = []
            sell_review = []
            watchlist = []
            action_plan = []
            
            # Start with available cash
            current_available_cash = float(portfolio_summary.get("cash_available", 0) if portfolio_summary.get("cash_available") != "UNAVAILABLE" else 0)
            
            for h in raw_holdings_analysis:
                decision_res = self.decision_engine.evaluate_holding(h, h["analysis"], portfolio_summary)
                action = decision_res.get("action", "HOLD")
                
                if action == "BUY_MORE":
                    sizing = self.position_sizer.suggest_allocation(
                        symbol=h.get("symbol"),
                        current_price=h.get("ltp", 0.0),
                        available_funds=current_available_cash,
                        portfolio_value=portfolio_summary.get("total_portfolio_value", 0),
                        risk_score=decision_res.get("risk_score", 50),
                        current_allocation_pct=decision_res.get("portfolio_allocation", 0.0),
                        confidence=decision_res.get("confidence", 1.0)
                    )
                    decision_res["quantity"] = sizing.get("suggested_quantity", 0)
                    decision_res["estimated_value"] = sizing.get("suggested_amount", 0.0)
                    decision_res["recommended_quantity_after_action"] = decision_res["current_quantity"] + decision_res["quantity"]
                    
                    if decision_res["quantity"] > 0:
                        decision_res["reasons"].append(sizing.get("sizing_reason", ""))
                        current_available_cash -= decision_res["estimated_value"]
                    else:
                        decision_res["action"] = "HOLD"
                        decision_res["reasons"].append("Insufficient remaining cash to accumulate.")
                        action = "HOLD"
                    
                elif action in ["SELL", "REDUCE"]:
                    reduction = self.position_sizer.suggest_reduction(
                        symbol=h.get("symbol"),
                        current_price=h.get("ltp", 0.0),
                        current_quantity=decision_res["current_quantity"],
                        thesis_status=decision_res["thesis_status"],
                        portfolio_value=portfolio_summary.get("total_portfolio_value", 0),
                        current_allocation_pct=decision_res.get("portfolio_allocation", 0.0)
                    )
                    decision_res["quantity"] = reduction.get("suggested_sell_quantity", 0)
                    decision_res["estimated_value"] = decision_res["quantity"] * decision_res["current_price"]
                    decision_res["recommended_quantity_after_action"] = reduction.get("resulting_quantity", 0)
                    decision_res["reasons"].append(reduction.get("reason", ""))
                
                h["decision"] = decision_res
                h["analysis"]["decision"] = decision_res["action"]
                holdings_analysis.append(h)
                action_plan.append(decision_res)
                
                if action == "SELL":
                    sell_review.append(h)
                elif action in ["WATCH", "NO_ACTION"]:
                    watchlist.append(h)
                    
            # 4. Market Buy Candidate Engine
            buy_candidates = self.candidate_ranker.discover_and_rank(limit=5)
            actual_buy_candidates = []
            
            for bc in buy_candidates:
                if bc["action"] == "BUY":
                    sizing = self.position_sizer.suggest_allocation(
                        symbol=bc["symbol"],
                        current_price=bc.get("current_price", 0.0),
                        available_funds=current_available_cash,
                        portfolio_value=portfolio_summary.get("total_portfolio_value", 0),
                        risk_score=bc["risk_score"],
                        current_allocation_pct=0.0,
                        confidence=bc.get("confidence", 1.0)
                    )
                    bc["quantity"] = sizing.get("suggested_quantity", 0)
                    bc["estimated_value"] = sizing.get("suggested_amount", 0.0)
                    bc["recommended_quantity_after_action"] = bc["quantity"]
                    
                    if bc["quantity"] > 0:
                        bc["reasons"].append(sizing.get("sizing_reason", ""))
                        actual_buy_candidates.append(bc)
                        action_plan.append(bc)
                        current_available_cash -= bc["estimated_value"]
                    else:
                        bc["action"] = "WATCH"
                        bc["reasons"].append("Insufficient funds to execute BUY. Ranked lower or cash exhausted.")
                        action_plan.append(bc)
                        watchlist.append(bc)
                else:
                    action_plan.append(bc)
                    watchlist.append(bc)
                
            # 6. Check Alerts
            self.alert_engine.check_portfolio_alerts(holdings_analysis, actual_buy_candidates)
            
            return {
                "status": "OK",
                "portfolio_summary": portfolio_summary,
                "daily_investment_action_plan": action_plan,
                "holdings_analysis": holdings_analysis,
                "buy_candidates": actual_buy_candidates,
                "candidates_analyzed_count": len(buy_candidates),
                "sell_review": sell_review,
                "watchlist": watchlist,
                "risk_summary": portfolio_summary.get("risk_indicators", {}),
                "data_freshness": {
                    "account_data": "FRESH",
                    "market_data": "MIXED",
                    "market_session": "UNKNOWN"
                },
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating portfolio analysis: {str(e)}")
            self.alert_engine.trigger_alert("BROKER_DISCONNECTED", f"Error during portfolio analysis: {str(e)}")
            return self._get_disconnected_response(f"Angel One API error or disconnected: {str(e)}")
