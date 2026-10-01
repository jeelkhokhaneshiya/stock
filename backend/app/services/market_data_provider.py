from typing import Dict, Any

class MockMarketDataProvider:
    def get_stock_data(self, symbol: str) -> Dict[str, Any]:
        # Return mock data based on symbol to provide deterministic test cases
        if "HDFCBANK" in symbol:
            return {"roe": 16, "debt_to_equity": 0.8, "pe_ratio": 18, "pb_ratio": 3, "rsi": 45, "current_price": 1600, "sma_200": 1500, "volatility": 0.2}
        if "WEAK" in symbol:
            return {"roe": 5, "debt_to_equity": 2.5, "pe_ratio": 60, "pb_ratio": 8, "rsi": 20, "current_price": 10, "sma_200": 50, "volatility": 0.6}
        return {"roe": 12, "debt_to_equity": 1.2, "pe_ratio": 22, "pb_ratio": 4, "rsi": 55, "current_price": 100, "sma_200": 90, "volatility": 0.3}