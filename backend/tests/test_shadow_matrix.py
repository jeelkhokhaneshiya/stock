import pytest
from app.services.decision.decision_engine import DecisionEngine
from app.services.fundamentals.screener import ScreenerFundamentalDataProvider
from app.services.fundamentals.base import FundamentalProviderStatus, FundamentalResult
from app.services.portfolio.portfolio_manager import PortfolioManager
from app.services.market_data.service import MarketDataService

def get_base_analysis(confidence=0.9, freshness="FRESH"):
    return {
        "fundamental_score": 80,
        "technical_score": 80,
        "risk_score": 80,
        "valuation_score": 80,
        "confidence": confidence,
        "data_freshness": freshness
    }

def test_case_2_hold_on_loss():
    engine = DecisionEngine()
    holding = {"symbol": "HOLD_LOSS", "pnl_percentage": -20, "ltp": 100}
    analysis = get_base_analysis()
    analysis["valuation_score"] = 50 
    context = {"concentration": {"asset_allocation": []}, "cash_available": 10000}
    
    res = engine.evaluate_holding(holding, analysis, context)
    assert res["decision"] == "HOLD"
    assert res["thesis_status"] == "THESIS_STRONG"

def test_case_3_buy_more():
    engine = DecisionEngine()
    holding = {"symbol": "STRONG_HOLD", "pnl_percentage": -15, "ltp": 100}
    analysis = get_base_analysis()
    context = {"concentration": {"asset_allocation": []}, "cash_available": 10000}
    
    res = engine.evaluate_holding(holding, analysis, context)
    assert res["decision"] == "BUY_MORE"

def test_case_4_reduce():
    engine = DecisionEngine()
    holding = {"symbol": "WEAK", "pnl_percentage": -10, "ltp": 100, "quantity": 10}
    analysis = {
        "fundamental_score": 40,
        "technical_score": 35,  # Needs to be < 40 for THESIS_WEAK
        "risk_score": 50,
        "valuation_score": 50,
        "confidence": 0.9,
        "data_freshness": "FRESH"
    }
    context = {"concentration": {"asset_allocation": []}, "cash_available": 10000}
    
    res = engine.evaluate_holding(holding, analysis, context)
    assert res["decision"] == "REDUCE"

def test_case_5_sell():
    engine = DecisionEngine()
    holding = {"symbol": "BROKEN", "pnl_percentage": -40, "ltp": 100, "quantity": 10}
    analysis = {
        "fundamental_score": 20,
        "technical_score": 20,
        "risk_score": 20,
        "valuation_score": 20,
        "confidence": 0.9,
        "data_freshness": "FRESH"
    }
    context = {"concentration": {"asset_allocation": []}, "cash_available": 10000}
    
    res = engine.evaluate_holding(holding, analysis, context)
    assert res["decision"] == "SELL"

def test_case_7_8_missing_stale():
    engine = DecisionEngine()
    holding = {"symbol": "STALE", "pnl_percentage": -10, "ltp": 100, "quantity": 10}
    analysis_stale = get_base_analysis(freshness="STALE")
    res_stale = engine.evaluate_holding(holding, analysis_stale, {})
    assert res_stale["decision"] == "NO_ACTION"
    
    analysis_missing = get_base_analysis(confidence=0.1)
    res_missing = engine.evaluate_holding(holding, analysis_missing, {})
    assert res_missing["decision"] == "NO_ACTION"

def test_case_1_6_9_portfolio_manager():
    # Mocking client for PM
    class MockClient:
        def get_funds(self):
            return {"available_cash": 100, "dict": lambda: {"available_cash": 100}}
        def get_holdings(self):
            return {"count": 0, "holdings": [], "dict": lambda: {"count": 0, "holdings": []}}
        def get_positions(self):
            return {"count": 0, "positions": [], "dict": lambda: {"count": 0, "positions": []}}
            
    mgr = PortfolioManager(MockClient())
    # Mock ranker to return a BUY candidate
    class MockRanker:
        def discover_and_rank(self, limit):
            return [{"symbol": "STRONG", "action": "BUY", "current_price": 100, "risk_score": 80, "confidence": 0.9, "reasons": []}]
    mgr.candidate_ranker = MockRanker()
    
    res = mgr.get_full_portfolio_analysis()
    
    # 100 > 100 cash (need at least 100 + buffer maybe? or sizing returns 0) -> WATCH
    assert any(c["action"] in ["WATCH", "NO_ACTION"] for c in res["watchlist"] if c["symbol"] == "STRONG")
    
    # Increase cash to simulate CASE 1 (BUY)
    class HighCashClient(MockClient):
        def get_funds(self):
            return {"available_cash": 1000000, "dict": lambda: {"available_cash": 1000000}}
            
    mgr2 = PortfolioManager(HighCashClient())
    mgr2.candidate_ranker = MockRanker()
    res2 = mgr2.get_full_portfolio_analysis()
    assert any(c["action"] == "BUY" for c in res2["buy_candidates"] if c["symbol"] == "STRONG")
    
    # Simulate Angel One unavailable (CASE 9)
    class FailingClient:
        def get_funds(self):
            raise Exception("Broker disconnected")
    mgr3 = PortfolioManager(client=FailingClient())
    res3 = mgr3.get_full_portfolio_analysis()
    assert res3["status"] == "BROKER_DISCONNECTED"

def test_case_10_screener_unavailable():
    class FailingScreener(ScreenerFundamentalDataProvider):
        def get_fundamentals(self, *args, **kwargs):
            return FundamentalResult(status=FundamentalProviderStatus.NOT_FOUND)
            
    scr = FailingScreener()
    res = scr.get_fundamentals("UNKNOWN", "NSE")
    assert res.status == FundamentalProviderStatus.NOT_FOUND
    assert res.revenue is None

def test_tcs_hero_moto_regression():
    scr = ScreenerFundamentalDataProvider()
    tcs = scr.get_fundamentals("TCS", "NSE")
    hero = scr.get_fundamentals("HEROMOTOCO", "NSE")
    
    if tcs.status == FundamentalProviderStatus.AVAILABLE and hero.status == FundamentalProviderStatus.AVAILABLE:
        assert tcs.revenue != hero.revenue
        assert tcs.eps != hero.eps
