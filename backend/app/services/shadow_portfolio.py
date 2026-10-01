from decimal import Decimal
from typing import Dict
from app.models.shadow import ShadowOrderRecord
from app.models.enums import OrderSide, ExecutionStatus

class ShadowPortfolioSimulator:
    def __init__(self, starting_cash: Decimal, starting_holdings: Dict[str, Decimal] = None):
        self.starting_cash = starting_cash
        self.starting_holdings = starting_holdings or {}
        
        self.current_cash = starting_cash
        self.current_holdings = self.starting_holdings.copy()
        
        self.simulated_buys = 0
        self.simulated_sells = 0
        self.hypothetical_pnl = Decimal("0")

    def process_order(self, order: ShadowOrderRecord):
        if order.status != ExecutionStatus.EXECUTED:
            return
            
        quantity = order.simulated_fill_quantity
        price = order.simulated_fill_price
        amount = quantity * price
        
        if order.side == OrderSide.BUY:
            if self.current_cash >= amount:
                self.current_cash -= amount
                self.current_holdings[order.symbol] = self.current_holdings.get(order.symbol, Decimal("0")) + quantity
                self.simulated_buys += 1
        elif order.side == OrderSide.SELL:
            current_qty = self.current_holdings.get(order.symbol, Decimal("0"))
            if current_qty >= quantity:
                self.current_cash += amount
                self.current_holdings[order.symbol] -= quantity
                if self.current_holdings[order.symbol] == Decimal("0"):
                    del self.current_holdings[order.symbol]
                self.simulated_sells += 1
                
    def get_portfolio_value(self, current_market_prices: Dict[str, Decimal]) -> Decimal:
        holdings_value = sum([qty * current_market_prices.get(sym, Decimal("0")) for sym, qty in self.current_holdings.items()])
        return self.current_cash + holdings_value
        
    def get_metrics(self, current_market_prices: Dict[str, Decimal]) -> dict:
        current_val = self.get_portfolio_value(current_market_prices)
        start_val = self.starting_cash + sum([qty * current_market_prices.get(sym, Decimal("0")) for sym, qty in self.starting_holdings.items()])
        
        pnl = current_val - start_val
        ret_pct = (pnl / start_val * Decimal("100")) if start_val > 0 else Decimal("0")
        
        return {
            "starting_cash": self.starting_cash,
            "remaining_cash": self.current_cash,
            "starting_holdings": self.starting_holdings,
            "current_holdings": self.current_holdings,
            "portfolio_value": current_val,
            "profit_loss": pnl,
            "return_percentage": ret_pct,
            "simulated_buys": self.simulated_buys,
            "simulated_sells": self.simulated_sells
        }
