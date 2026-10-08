import pytest
from unittest.mock import MagicMock
from app.services.decision.decision_engine import DecisionEngine

def test_regression_stale_data():
    engine = DecisionEngine()
    holding = {"symbol": "RELIANCE", "pnl_percentage": 0, "ltp": 2500, "quantity": 10}
    analysis = {
        "fundamental_score": 80,
        "technical_score": 80,
        "confidence": 0.8,
        "data_freshness": "STALE"
    }
    context = {"concentration": {"asset_allocation": []}}
    res = engine.evaluate_holding(holding, analysis, context)
    assert res["decision"] == "NO_ACTION"
    assert res["thesis_status"] == "INSUFFICIENT_DATA"
    assert any("stale" in r.lower() for r in res["reasons"])

def test_regression_missing_fundamentals_unavailable():
    engine = DecisionEngine()
    holding = {"symbol": "RELIANCE", "pnl_percentage": -5, "ltp": 2500, "quantity": 10}
    # When fundamentals are UNAVAILABLE, fundamental_score might be low or confidence might be very low
    analysis = {
        "fundamental_score": 0,
        "technical_score": 50,
        "confidence": 0.1,  # low confidence due to missing fundamentals
        "data_freshness": "FRESH"
    }
    context = {"concentration": {"asset_allocation": []}}
    res = engine.evaluate_holding(holding, analysis, context)
    assert res["decision"] == "NO_ACTION"
    assert res["thesis_status"] == "INSUFFICIENT_DATA"

from app.services.portfolio.portfolio_analyzer import PortfolioAnalyzer

def test_regression_portfolio_pnl_mathematically_correct():
    analyzer = PortfolioAnalyzer()
    funds = {"available_cash": 1000.0}
    holdings = {
        "holdings": [
            {"symbol": "TCS", "average_price": 3000, "last_price": 3500, "quantity": 10},
            {"symbol": "INFY", "average_price": 1500, "last_price": 1400, "quantity": 20}
        ]
    }
    positions = {"positions": []}
    
    res = analyzer.analyze_portfolio(funds, holdings, positions)
    
    # TCS invested = 30000, current = 35000, pnl = +5000
    # INFY invested = 30000, current = 28000, pnl = -2000
    # Total invested = 60000, current = 63000, unrealized pnl = +3000
    
    assert res["invested_value"] == 60000.0
    assert res["current_value"] == 63000.0
    assert res["unrealized_pnl"] == 3000.0
    assert res["cash_available"] == 1000.0
    assert res["total_portfolio_value"] == 64000.0

