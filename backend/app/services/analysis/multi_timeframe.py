from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone
from app.services.market_data.service import MarketDataService
from app.services.analysis.technical import TechnicalAnalyzer

class MultiTimeframeAnalyzer:
    def __init__(self, market_data_service: MarketDataService):
        self.market_data_service = market_data_service
        self.technical_analyzer = TechnicalAnalyzer()
        
    def analyze(self, symbol: str, exchange: str = "NSE") -> Dict[str, Any]:
        """
        Analyzes a candidate across multiple timeframes.
        """
        timeframes = {
            "5m": {"interval": "FIVE_MINUTE", "days": 5},
            "15m": {"interval": "FIFTEEN_MINUTE", "days": 10},
            "1H": {"interval": "ONE_HOUR", "days": 60},
            "Daily": {"interval": "ONE_DAY", "days": 365},
        }
        
        results = {}
        end_date = datetime.now(timezone.utc)
        
        for name, config in timeframes.items():
            import time
            time.sleep(0.4)
            start_date = end_date - timedelta(days=config["days"])
            try:
                bars = self.market_data_service.get_historical_data(
                    symbol=symbol,
                    exchange=exchange,
                    timeframe=config["interval"],
                    start_date=start_date,
                    end_date=end_date
                )
                
                if bars:
                    res = self.technical_analyzer.analyze_bars(bars)
                    # Include freshness
                    res["freshness"] = "STALE" if any(getattr(b, 'is_stale', False) for b in bars) else "FRESH"
                    results[name] = res
                else:
                    results[name] = {"status": "UNAVAILABLE", "error": "No data returned"}
            except Exception as e:
                error_str = str(e)
                results[name] = {"status": "ERROR", "error": error_str}
                if "permissions denied" in error_str.lower() or "403" in error_str:
                    # Do not repeatedly query other timeframes if the API is denied
                    for other_name in timeframes:
                        if other_name not in results:
                            results[other_name] = {"status": "UNAVAILABLE", "error": "API access denied"}
                    break

        # Synthesize multi-timeframe score
        short_term_trend = results.get("15m", {}).get("trend", "NEUTRAL")
        medium_term_trend = results.get("1H", {}).get("trend", "NEUTRAL")
        long_term_trend = results.get("Daily", {}).get("trend", "NEUTRAL")

        trend_alignment = "NEUTRAL"
        if short_term_trend in ["BULLISH", "STRONG_BULLISH"] and medium_term_trend in ["BULLISH", "STRONG_BULLISH"] and long_term_trend in ["BULLISH", "STRONG_BULLISH"]:
            trend_alignment = "STRONG_BULLISH"
        elif short_term_trend in ["BEARISH", "STRONG_BEARISH"] and medium_term_trend in ["BEARISH", "STRONG_BEARISH"] and long_term_trend in ["BEARISH", "STRONG_BEARISH"]:
            trend_alignment = "STRONG_BEARISH"

        scores = [res.get("technical_score", 50) for name, res in results.items() if res.get("status") == "SUCCESS"]
        mtf_score = sum(scores) / len(scores) if scores else 50.0

        return {
            "timeframes": results,
            "summary": {
                "short_term_trend": short_term_trend,
                "medium_term_trend": medium_term_trend,
                "long_term_trend": long_term_trend,
                "trend_alignment": trend_alignment,
                "multi_timeframe_score": mtf_score,
                "confidence": 0.8 if len(scores) >= 3 else 0.4
            }
        }
