import pytest
from unittest.mock import MagicMock, patch
from app.services.decision.candidate_ranker import CandidateRanker

def test_candidate_ranker_discovery_and_filtering():
    ranker = CandidateRanker()
    # Mock scanner
    ranker.scanner = MagicMock()
    ranker.scanner.discover_opportunities.return_value = {
        "candidates": [
            {"symbol": "RELIANCE-EQ"},
            {"symbol": "TCS-EQ"},
            {"symbol": "INVALID"}
        ]
    }
    
    # Mock MTF analyzer
    ranker.mtf = MagicMock()
    ranker.mtf.analyze.side_effect = lambda sym, exch: {
        "timeframes": {"Daily": {"close": 100.0, "volatility": 0.02, "freshness": "FRESH"}},
        "summary": {"multi_timeframe_score": 80.0, "confidence": 0.8}
    }
    
    # Mock Fundamental analyzer
    ranker.fundamental = MagicMock()
    ranker.fundamental.analyze_fundamentals.side_effect = lambda sym, data: {
        "fundamental_score": 90.0,
        "confidence": 0.9,
        "metrics": {"roe": 20.0}
    }
    
    # Mock Risk analyzer
    ranker.risk = MagicMock()
    ranker.risk.analyze.return_value = (85.0, {}, [])
    
    # Rank candidates
    candidates = ranker.discover_and_rank(limit=2)
    
    assert len(candidates) == 2
    assert candidates[0]["symbol"] in ["RELIANCE-EQ", "TCS-EQ"]
    assert candidates[0]["action"] == "BUY"
    assert "Strong technical trend" in candidates[0]["reasons"][0]
    
def test_candidate_ranker_stale_data_rejection():
    ranker = CandidateRanker()
    ranker.scanner = MagicMock()
    ranker.scanner.discover_opportunities.return_value = {"candidates": [{"symbol": "STALE-EQ"}]}
    
    ranker.mtf = MagicMock()
    ranker.mtf.analyze.return_value = {
        "timeframes": {"Daily": {"freshness": "STALE"}},
        "summary": {"multi_timeframe_score": 90.0, "confidence": 0.8}
    }
    
    ranker.fundamental = MagicMock()
    ranker.fundamental.analyze_fundamentals.return_value = {"fundamental_score": 90.0}
    
    ranker.risk = MagicMock()
    ranker.risk.analyze.return_value = (90.0, {}, [])
    
    candidates = ranker.discover_and_rank(limit=1)
    
    assert len(candidates) == 1
    assert candidates[0]["action"] == "NO_ACTION"
    assert "Data is stale" in candidates[0]["reasons"][0]

def test_candidate_ranker_high_risk_rejection():
    ranker = CandidateRanker()
    ranker.scanner = MagicMock()
    ranker.scanner.discover_opportunities.return_value = {"candidates": [{"symbol": "RISKY-EQ"}]}
    
    ranker.mtf = MagicMock()
    ranker.mtf.analyze.return_value = {
        "timeframes": {"Daily": {"freshness": "FRESH"}},
        "summary": {"multi_timeframe_score": 90.0, "confidence": 1.0}
    }
    
    ranker.fundamental = MagicMock()
    ranker.fundamental.analyze_fundamentals.return_value = {"fundamental_score": 90.0, "confidence": 1.0}
    
    ranker.risk = MagicMock()
    # Risk score 30 < 40 threshold
    ranker.risk.analyze.return_value = (30.0, {}, ["High volatility"])
    
    candidates = ranker.discover_and_rank(limit=1)
    
    assert candidates[0]["action"] == "NO_ACTION"
    assert "Risk is excessive" in candidates[0]["reasons"][0]
