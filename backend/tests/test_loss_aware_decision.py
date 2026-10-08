import pytest
from app.services.decision.decision_engine import DecisionEngine

def test_loss_does_not_automatically_cause_sell():
    engine = DecisionEngine()
    holding = {"symbol": "TEST", "pnl_percentage": -10, "ltp": 100}
    # Strong thesis despite loss
    analysis = {
        "fundamental_score": 80,
        "technical_score": 70,
        "risk_score": 70,
        "valuation_score": 50, # not attractive enough to accumulate
        "confidence": 0.8,
        "data_freshness": "FRESH"
    }
    context = {"concentration": {"asset_allocation": [{"symbol": "TEST", "percentage": 5}]}}
    
    res = engine.evaluate_holding(holding, analysis, context)
    assert res["thesis_status"] == "THESIS_STRONG"
    assert res["decision"] == "HOLD"
    assert any("Do not sell despite the loss" in r for r in res["reasons"])

def test_strong_thesis_attractive_valuation_loss_causes_accumulate():
    engine = DecisionEngine()
    holding = {"symbol": "TEST", "pnl_percentage": -15, "ltp": 100}
    analysis = {
        "fundamental_score": 80,
        "technical_score": 70,
        "risk_score": 70,
        "valuation_score": 80, # Attractive valuation
        "confidence": 0.8,
        "data_freshness": "FRESH"
    }
    context = {"concentration": {"asset_allocation": [{"symbol": "TEST", "percentage": 5}]}}
    
    res = engine.evaluate_holding(holding, analysis, context)
    assert res["thesis_status"] == "THESIS_STRONG"
    assert res["decision"] == "BUY_MORE"
    assert any("Safe to average down" in r for r in res["reasons"])

def test_weak_thesis_loss_causes_reduce_review():
    engine = DecisionEngine()
    holding = {"symbol": "TEST", "pnl_percentage": -5, "ltp": 100}
    analysis = {
        "fundamental_score": 40,
        "technical_score": 35,
        "risk_score": 50,
        "valuation_score": 50,
        "confidence": 0.8,
        "data_freshness": "FRESH"
    }
    context = {"concentration": {"asset_allocation": [{"symbol": "TEST", "percentage": 5}]}}
    
    res = engine.evaluate_holding(holding, analysis, context)
    assert res["thesis_status"] == "THESIS_WEAK"
    assert res["decision"] == "REDUCE"

def test_broken_thesis_causes_sell_review():
    engine = DecisionEngine()
    holding = {"symbol": "TEST", "pnl_percentage": -30, "ltp": 100}
    analysis = {
        "fundamental_score": 20,
        "technical_score": 20,
        "risk_score": 20,
        "valuation_score": 50,
        "confidence": 0.8,
        "data_freshness": "FRESH"
    }
    context = {"concentration": {"asset_allocation": [{"symbol": "TEST", "percentage": 5}]}}
    
    res = engine.evaluate_holding(holding, analysis, context)
    assert res["thesis_status"] == "THESIS_BROKEN"
    assert res["decision"] == "SELL"

def test_insufficient_data_causes_watch():
    engine = DecisionEngine()
    holding = {"symbol": "TEST", "pnl_percentage": -10, "ltp": 100, "quantity": 5}
    analysis = {
        "confidence": 0.1, # Too low
        "data_freshness": "FRESH"
    }
    context = {"concentration": {"asset_allocation": []}}
    
    res = engine.evaluate_holding(holding, analysis, context)
    assert res["thesis_status"] == "INSUFFICIENT_DATA"
    assert res["decision"] == "NO_ACTION"

def test_stale_data_causes_watch():
    engine = DecisionEngine()
    holding = {"symbol": "TEST", "pnl_percentage": 10, "ltp": 100, "quantity": 5}
    analysis = {
        "fundamental_score": 90,
        "technical_score": 90,
        "confidence": 0.9,
        "data_freshness": "STALE"
    }
    context = {"concentration": {"asset_allocation": []}}
    
    res = engine.evaluate_holding(holding, analysis, context)
    assert res["thesis_status"] == "INSUFFICIENT_DATA"
    assert res["decision"] == "NO_ACTION"

def test_profit_strong_thesis_causes_hold():
    engine = DecisionEngine()
    holding = {"symbol": "TEST", "pnl_percentage": 50, "ltp": 100}
    analysis = {
        "fundamental_score": 80,
        "technical_score": 80,
        "risk_score": 80,
        "valuation_score": 50,
        "confidence": 0.9,
        "data_freshness": "FRESH"
    }
    context = {"concentration": {"asset_allocation": [{"symbol": "TEST", "percentage": 15}]}}
    
    res = engine.evaluate_holding(holding, analysis, context)
    assert res["thesis_status"] == "THESIS_STRONG"
    assert res["decision"] == "HOLD"

def test_profit_excessive_valuation_causes_reduce_review():
    engine = DecisionEngine()
    holding = {"symbol": "TEST", "pnl_percentage": 100, "ltp": 100}
    analysis = {
        "fundamental_score": 80,
        "technical_score": 80,
        "risk_score": 80,
        "valuation_score": 10, # Very stretched
        "confidence": 0.9,
        "data_freshness": "FRESH"
    }
    context = {"concentration": {"asset_allocation": [{"symbol": "TEST", "percentage": 15}]}}
    
    res = engine.evaluate_holding(holding, analysis, context)
    assert res["decision"] == "REDUCE"
    assert any("Valuation is extremely stretched" in r for r in res["reasons"])
    
def test_concentration_limit_causes_reduce_review():
    engine = DecisionEngine()
    holding = {"symbol": "TEST", "pnl_percentage": 20, "ltp": 100}
    analysis = {
        "fundamental_score": 80,
        "technical_score": 80,
        "risk_score": 80,
        "valuation_score": 50,
        "confidence": 0.9,
        "data_freshness": "FRESH"
    }
    context = {"concentration": {"asset_allocation": [{"symbol": "TEST", "percentage": 35}]}} # > 30%
    
    res = engine.evaluate_holding(holding, analysis, context)
    assert res["decision"] == "REDUCE"
    assert any("High portfolio concentration" in r for r in res["reasons"])
