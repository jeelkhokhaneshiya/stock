import pytest
from app.services.analysis.service import InvestmentAnalysisService

def test_missing_data_reduces_confidence():
    service = InvestmentAnalysisService()
    # Missing all data
    report = service.execute_full_analysis("TCS", "STOCK", {})
    assert report["analysis_confidence"] == "INSUFFICIENT"
    assert len(report["missing_data"]) > 0

def test_strong_fundamentals():
    service = InvestmentAnalysisService()
    context = {
        "revenue_growth": 0.15,
        "eps_growth": 0.12,
        "roe": 0.18,
        "debt_to_equity": 0.5,
        "free_cash_flow": 1000,
        "pe_ratio": 20,
        "pb_ratio": 3,
        "long_term_trend": "UP",
        "max_drawdown": 0.10,
        "rsi_14_weekly": 45,
        "profit_consistent_5y": True,
        "business_moat": "WIDE",
        "management_quality": "HIGH",
        "volatility": 0.20
    }
    report = service.execute_full_analysis("TCS", "STOCK", context)
    assert report["analysis_confidence"] == "HIGH"
    assert report["long_term_suitability_score"] > 80

def test_excessive_valuation():
    service = InvestmentAnalysisService()
    context = {
        "pe_ratio": 60, # excessive
        "debt_to_equity": 0.5,
    }
    report = service.execute_full_analysis("TCS", "STOCK", context)
    # Risk score should drop
    assert report["risk_score"] < 100
    assert "Extreme valuation multiples" in report["warnings"]

def test_stale_market_data_block():
    service = InvestmentAnalysisService()
    context = {
        "data_freshness_seconds": 4000 # > 3600
    }
    report = service.execute_full_analysis("TCS", "STOCK", context)
    assert report["analysis_confidence"] == "INSUFFICIENT"
    assert "STALE_MARKET_DATA" in report["blocking_reasons"]
