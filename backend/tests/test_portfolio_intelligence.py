import pytest
from datetime import datetime, timezone
from app.services.portfolio.portfolio_manager import PortfolioManager
from app.services.portfolio.alert_engine import AlertEngine
from app.services.decision.decision_engine import DecisionEngine
from app.services.decision.candidate_ranker import CandidateRanker
from app.services.portfolio.position_sizer import PositionSizer
from unittest.mock import MagicMock

def test_alert_engine_duplicate_protection():
    engine = AlertEngine()
    engine.trigger_alert("TEST_ALERT", "Test message", {"symbol": "RELIANCE"})
    assert len(engine.alerts) == 1
    
    # Trigger same alert again, should be deduplicated
    engine.trigger_alert("TEST_ALERT", "Test message again", {"symbol": "RELIANCE"})
    assert len(engine.alerts) == 1

    # Trigger different symbol
    engine.trigger_alert("TEST_ALERT", "Test message again", {"symbol": "TCS"})
    assert len(engine.alerts) == 2

def test_decision_engine_sell_review():
    engine = DecisionEngine()
    
    holding = {"symbol": "WEAK_STOCK", "pnl_percentage": -25.0}
    analysis = {"technical_score": 20.0, "fundamental_score": 30.0, "risk_score": 80.0, "data_freshness": "FRESH", "confidence": 1.0}
    portfolio_context = {}
    
    decision = engine.evaluate_holding(holding, analysis, portfolio_context)
    
    assert decision["decision"] == "SELL"
    assert len(decision["reasons"]) > 0

def test_decision_engine_hold():
    engine = DecisionEngine()
    
    holding = {"symbol": "STRONG_STOCK", "pnl_percentage": 10.0}
    analysis = {"technical_score": 80.0, "fundamental_score": 80.0, "risk_score": 80.0, "data_freshness": "FRESH", "confidence": 1.0}
    portfolio_context = {}
    
    decision = engine.evaluate_holding(holding, analysis, portfolio_context)
    
    assert decision["decision"] == "HOLD"

def test_position_sizer():
    sizer = PositionSizer()
    
    # High conviction
    size = sizer.suggest_allocation(
        symbol="TCS",
        current_price=100.0,
        available_funds=50000.0,
        portfolio_value=100000.0,
        risk_score=85.0,
        current_allocation_pct=0.0
    )
    
    assert size["suggested_allocation_percent"] > 0.0
    assert size["suggested_amount"] > 0.0

    # Low conviction / high risk
    size_risky = sizer.suggest_allocation(
        symbol="PENNY",
        current_price=10.0,
        available_funds=50000.0,
        portfolio_value=100000.0,
        risk_score=20.0,
        current_allocation_pct=0.0
    )
    assert size_risky["suggested_allocation_percent"] == 0.0

def test_candidate_ranker():
    ranker = CandidateRanker()
    # Mock data directly returning candidates to avoid full market fetch
    # We bypass discover_and_rank internal discovery
    pass

@pytest.mark.asyncio
async def test_portfolio_manager_full_flow():
    # Setup mock broker and market data
    broker_mock = MagicMock()
    broker_mock.authenticated = True
    broker_mock.get_account.return_value = {"client_id": "TEST", "broker": "angel_one"}
    broker_mock.get_funds.return_value = {"data": {"availablecash": "50000", "netcash": "50000", "total_pnl": "1000"}, "status": True}
    broker_mock.get_holdings.return_value = {"data": [
        {"tradingsymbol": "TCS-EQ", "quantity": 10, "averageprice": 3000.0, "ltp": 3500.0, "pnlpercentage": 16.6}
    ], "status": True}
    broker_mock.get_positions.return_value = {"data": [], "status": True}
    
    manager = PortfolioManager(client=broker_mock)
    
    # Mock inner methods to isolate tests
    manager.holding_analyzer.analyze_holdings = MagicMock(return_value=[{
        "symbol": "TCS", "quantity": 10, "average_price": 3000.0, "current_price": 3500.0, "pnl_percentage": 16.6, "ltp": 3500.0,
        "analysis": {"technical_score": 75.0, "fundamental_score": 80.0, "risk_score": 80.0, "decision": "HOLD", "data_freshness": "FRESH", "confidence": 1.0}
    }])
    
    manager.candidate_ranker.discover_and_rank = MagicMock(return_value=[])

    analysis = manager.get_full_portfolio_analysis()
    
    assert "error" not in analysis
    assert "portfolio_summary" in analysis
    assert len(analysis["holdings_analysis"]) == 1
    assert analysis["holdings_analysis"][0]["symbol"] == "TCS"
    assert analysis["holdings_analysis"][0]["decision"]["decision"] == "HOLD"
