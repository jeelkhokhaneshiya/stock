import pytest
from datetime import datetime, timezone
from app.services.market_data.angel_one import AngelOneMarketDataProvider
from unittest.mock import MagicMock

def test_angel_one_ohlc_parsing():
    client_mock = MagicMock()
    # Mock Angel One response
    client_mock.get_candle_data.return_value = [
        ["2023-01-01T09:15:00+05:30", "100.0", "105.0", "95.0", "102.0", "10000"],
        ["2023-01-01T09:30:00+05:30", "102.0", "110.0", "101.0", "108.0", "15000"],
        # Invalid candle (high < low) should be rejected
        ["2023-01-01T09:45:00+05:30", "108.0", "90.0", "100.0", "95.0", "5000"],
        # Invalid volume
        ["2023-01-01T10:00:00+05:30", "95.0", "100.0", "90.0", "98.0", "-100"]
    ]
    
    provider = AngelOneMarketDataProvider(client_mock)
    start = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end = datetime(2023, 1, 2, tzinfo=timezone.utc)
    
    bars = provider.get_historical_data("12345", "NSE", "FIFTEEN_MINUTE", start, end)
    
    # Expect only 2 valid bars
    assert len(bars) == 2
    
    # Check first bar parsing
    assert bars[0].open == 100.0
    assert bars[0].high == 105.0
    assert bars[0].low == 95.0
    assert bars[0].close == 102.0
    assert bars[0].volume == 10000
