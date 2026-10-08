import pytest
import os
from app.services.portfolio.holding_analyzer import HoldingAnalyzer

def test_company_specific_scoring():
    from unittest.mock import patch
    with patch("app.core.config.settings.MARKET_DATA_PROVIDER", "mock"):
        analyzer = HoldingAnalyzer()
    
        holdings_data = {
            "holdings": [
                {"symbol": "TCS", "exchange": "NSE", "quantity": 10, "average_price": 100, "last_price": 120},
                {"symbol": "INFY", "exchange": "NSE", "quantity": 10, "average_price": 100, "last_price": 120},
            ]
        }
    
        results = analyzer.analyze_holdings(holdings_data)
    
        assert len(results) == 2
    
        mv = next(r for r in results if r["symbol"] == "TCS")
        hm = next(r for r in results if r["symbol"] == "INFY")
    
        assert mv["analysis"]["fundamental_score"] != hm["analysis"]["fundamental_score"]
