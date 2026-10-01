from decimal import Decimal
from typing import List, Dict, Any
from app.schemas.allocation import PortfolioHoldingInfo, PortfolioAnalysisReport, PortfolioData
from app.services.market_data.service import MarketDataService

class PortfolioAnalysisService:
    def __init__(self, market_data_service: MarketDataService):
        self.market_data_service = market_data_service

    def analyze(self, portfolio: PortfolioData) -> PortfolioAnalysisReport:
        holdings_info: List[PortfolioHoldingInfo] = []
        invested_value = Decimal("0.0")
        
        largest_sym = None
        smallest_sym = None
        largest_val = Decimal("-1")
        smallest_val = Decimal("9999999999")
        
        for holding in portfolio.holdings:
            # We mock the current price if market data service fails for now, or just fetch it
            try:
                quote = self.market_data_service.get_quote(holding.symbol)
                current_price = Decimal(str(quote.price))
            except Exception:
                current_price = holding.average_cost
                
            qty = holding.quantity
            avg_cost = holding.average_cost
            
            market_val = qty * current_price
            invested_value += market_val
            
            pnl = market_val - (qty * avg_cost)
            pnl_pct = (pnl / (qty * avg_cost)) * Decimal("100") if qty * avg_cost > 0 else Decimal("0")
            
            if market_val > largest_val:
                largest_val = market_val
                largest_sym = holding.symbol
                
            if market_val < smallest_val and market_val > 0:
                smallest_val = market_val
                smallest_sym = holding.symbol
                
            holdings_info.append(
                PortfolioHoldingInfo(
                    symbol=holding.symbol,
                    asset_type=holding.asset_type,
                    quantity=qty,
                    average_cost=avg_cost,
                    current_price=current_price,
                    market_value=market_val,
                    unrealized_pnl=pnl,
                    unrealized_pnl_percent=pnl_pct
                )
            )
            
        avail_cash = portfolio.cash_balance
        total_val = avail_cash + invested_value
        cash_pct = (avail_cash / total_val) * Decimal("100") if total_val > 0 else Decimal("100")
        
        return PortfolioAnalysisReport(
            portfolio_id=str(portfolio.id),
            total_portfolio_value=total_val,
            invested_value=invested_value,
            available_cash=avail_cash,
            cash_percentage=cash_pct,
            number_of_holdings=len(holdings_info),
            holdings=holdings_info,
            largest_position_symbol=largest_sym,
            smallest_position_symbol=smallest_sym
        )
