import pytest
from app.services.discovery.scanner import MarketScanner
from unittest.mock import patch, MagicMock

class TestMarketScanner:
    def test_filter_eligible_candidates(self):
        scanner = MarketScanner()
        mock_data = [
            {"exch_seg": "NSE", "symbol": "RELIANCE-EQ", "name": "RELIANCE"},
            {"exch_seg": "BSE", "symbol": "TCS", "name": "TCS"},
            {"exch_seg": "NFO", "symbol": "NIFTY", "name": "NIFTY"}
        ]
        
        eligible = scanner.filter_eligible_candidates(mock_data)
        assert len(eligible) == 1
        assert eligible[0]["symbol"] == "RELIANCE-EQ"

    @patch("app.services.discovery.scanner.httpx.Client.get")
    def test_discover_opportunities(self, mock_get):
        scanner = MarketScanner()
        
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"exch_seg": "NSE", "symbol": "RELIANCE-EQ", "name": "RELIANCE"},
            {"exch_seg": "BSE", "symbol": "TCS", "name": "TCS"}
        ]
        mock_get.return_value = mock_response
        
        res = scanner.discover_opportunities()
        assert res["total_discovered"] == 1
        assert res["candidates"][0]["symbol"] == "RELIANCE-EQ"
