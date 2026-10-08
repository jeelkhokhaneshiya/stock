import pytest
from datetime import datetime, timezone, timedelta
from app.services.analysis.technical import TechnicalAnalyzer
from app.schemas.market_data import HistoricalBar

def generate_mock_bars(count=200):
    bars = []
    base_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
    base_price = 100.0
    for i in range(count):
        # Create an uptrend
        close = base_price + (i * 0.5)
        bar = HistoricalBar(
            symbol="MOCK",
            exchange="NSE",
            data_source="MOCK",
            timestamp=base_time + timedelta(days=i),
            open=close - 1,
            high=close + 2,
            low=close - 2,
            close=close,
            volume=1000 + i
        )
        bars.append(bar)
    return bars

def test_technical_analyzer_success():
    bars = generate_mock_bars(200)
    analyzer = TechnicalAnalyzer()
    res = analyzer.analyze_bars(bars)
    
    assert res["status"] == "SUCCESS"
    assert res["trend"] in ["BULLISH", "STRONG_BULLISH"]
    assert res["indicators"]["sma_20"] is not None
    assert res["indicators"]["rsi_14"] is not None
    assert res["indicators"]["macd"] is not None

def test_technical_analyzer_insufficient_data():
    bars = generate_mock_bars(10)
    analyzer = TechnicalAnalyzer()
    res = analyzer.analyze_bars(bars)
    
    assert res["status"] == "UNAVAILABLE"
    assert "error" in res
