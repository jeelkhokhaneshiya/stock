from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Any
from datetime import datetime, timedelta, timezone
from app.api import deps
from app.models.user import User
from app.services.market_data.factory import get_market_data_service
from app.services.analysis.technical import TechnicalAnalyzer
from app.services.analysis.fundamental import FundamentalAnalyzer
from app.services.analysis.multi_timeframe import MultiTimeframeAnalyzer

router = APIRouter()

@router.get("/ohlc/{symbol}")
def get_ohlc(
    symbol: str,
    exchange: str = "NSE",
    interval: str = Query("FIFTEEN_MINUTE", description="Angel One interval e.g. ONE_MINUTE, FIFTEEN_MINUTE, ONE_DAY"),
    days: int = Query(5, description="Number of past days"),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    service = get_market_data_service()
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        bars = service.get_historical_data(symbol, exchange, interval, start_date, end_date)
        
        is_stale = False
        if bars:
            age = (end_date - bars[-1].timestamp).total_seconds()
            if age > 86400 * 2: # Older than 2 days
                is_stale = True
        
        return {
            "symbol": symbol,
            "exchange": exchange,
            "interval": interval,
            "candle_count": len(bars),
            "fetched_at": end_date.isoformat(),
            "source": "ANGEL_ONE",
            "freshness": "STALE" if is_stale else "FRESH",
            "data_start": bars[0].timestamp.isoformat() if bars else None,
            "data_end": bars[-1].timestamp.isoformat() if bars else None,
            "candles": [
                {
                    "timestamp": b.timestamp.isoformat(),
                    "open": b.open,
                    "high": b.high,
                    "low": b.low,
                    "close": b.close,
                    "volume": b.volume
                } for b in bars
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/technical/{symbol}")
def get_technical(
    symbol: str,
    exchange: str = "NSE",
    interval: str = Query("ONE_DAY", description="Angel One interval"),
    days: int = Query(365, description="Number of past days for TA"),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    service = get_market_data_service()
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        bars = service.get_historical_data(symbol, exchange, interval, start_date, end_date)
        
        analyzer = TechnicalAnalyzer()
        res = analyzer.analyze_bars(bars)
        
        # Include freshness
        is_stale = any(getattr(b, 'is_stale', False) for b in bars) if bars else True
        res["freshness"] = "STALE" if is_stale else "FRESH"
        res["symbol"] = symbol
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/fundamentals/{symbol}")
def get_fundamentals(
    symbol: str,
    exchange: str = "NSE",
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    service = get_market_data_service()
    try:
        # Fetch from provider (if supported)
        try:
            fund_data = service.get_fundamentals(symbol, exchange)
        except NotImplementedError:
            fund_data = None # Angel One doesn't provide this natively in standard way
            
        analyzer = FundamentalAnalyzer()
        res = analyzer.analyze_fundamentals(symbol, fund_data)
        res["symbol"] = symbol
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/analysis/{symbol}")
def get_combined_analysis(
    symbol: str,
    exchange: str = "NSE",
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    service = get_market_data_service()
    try:
        # 1. Multi-timeframe Technical Analysis
        mtf_analyzer = MultiTimeframeAnalyzer(service)
        mtf_res = mtf_analyzer.analyze(symbol, exchange)
        
        # 2. Fundamentals
        try:
            fund_data = service.get_fundamentals(symbol, exchange)
        except NotImplementedError:
            fund_data = None
        fund_analyzer = FundamentalAnalyzer()
        fund_res = fund_analyzer.analyze_fundamentals(symbol, fund_data)
        
        # 3. Combine scores
        tech_score = mtf_res.get("summary", {}).get("multi_timeframe_score", 50.0)
        fund_score = fund_res.get("fundamental_score", 50.0)
        
        overall_score = (tech_score * 0.7) + (fund_score * 0.3)
        
        # 4. Classification
        classification = "WATCH"
        if overall_score > 75:
            classification = "BUY_CANDIDATE"
        elif overall_score > 60:
            classification = "HOLD"
        elif overall_score < 40:
            classification = "AVOID"
            
        risk_flags = mtf_res.get("summary", {}).get("warnings", []) + fund_res.get("warnings", [])
        
        return {
            "symbol": symbol,
            "company_name": symbol, # Map to name if available
            "technical_score": tech_score,
            "fundamental_score": fund_score,
            "risk_flags": risk_flags,
            "data_quality": "PARTIAL" if fund_data is None else "FULL",
            "overall_score": overall_score,
            "confidence": min(mtf_res.get("summary", {}).get("confidence", 0), fund_res.get("confidence", 0)),
            "classification": classification,
            "multi_timeframe": mtf_res,
            "fundamentals": fund_res
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
