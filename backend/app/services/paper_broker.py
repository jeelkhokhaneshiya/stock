from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Any, List, Optional
from app.services.interfaces import BrokerAdapter, TransactionCostCalculator
from app.models.enums import AssetType, OrderSide, OrderStatus
from app.models.paper import PaperAccount, PaperHolding, PaperOrder

class DefaultTransactionCostCalculator(TransactionCostCalculator):
    def calculate_cost(self, side: OrderSide, quantity: float, price: float, asset_type: AssetType) -> float:
        return 0.0

class PaperBroker(BrokerAdapter):
    def __init__(self, db: Session, account_id: int, tx_calculator: Optional[TransactionCostCalculator] = None):
        self.db = db
        self.account_id = account_id
        self.tx_calculator = tx_calculator or DefaultTransactionCostCalculator()

    def _get_account(self) -> PaperAccount:
        acc = self.db.query(PaperAccount).filter(PaperAccount.id == self.account_id).first()
        if not acc:
            raise ValueError(f"PaperAccount {self.account_id} not found")
        return acc

    def authenticate(self) -> bool:
        return True

    def get_account_balance(self) -> float:
        acc = self._get_account()
        return acc.initial_cash

    def get_available_cash(self) -> float:
        acc = self._get_account()
        return acc.available_cash

    def get_positions(self) -> List[Any]:
        return self.get_holdings()

    def get_holdings(self) -> List[Any]:
        return self.db.query(PaperHolding).filter(PaperHolding.paper_account_id == self.account_id).all()

    def get_quote(self, symbol: str) -> float:
        raise NotImplementedError("Market Data not implemented in Phase 2")

    def get_order(self, client_order_id: str) -> Any:
        return self.db.query(PaperOrder).filter(
            PaperOrder.paper_account_id == self.account_id,
            PaperOrder.client_order_id == client_order_id
        ).first()

    def get_orders(self) -> List[Any]:
        return self.db.query(PaperOrder).filter(PaperOrder.paper_account_id == self.account_id).all()

    def _process_order(self, client_order_id: str, symbol: str, quantity: float, price: float, asset_type: AssetType, side: OrderSide):
        if quantity <= 0 or price <= 0:
            raise ValueError("Quantity and price must be positive")
        
        if asset_type not in [AssetType.STOCK, AssetType.ETF]:
            raise ValueError("UNSUPPORTED_INSTRUMENT_FOR_PAPER_EXECUTION")

        existing_order = self.get_order(client_order_id)
        if existing_order:
            return existing_order

        acc = self._get_account()
        
        order = PaperOrder(
            paper_account_id=self.account_id,
            client_order_id=client_order_id,
            symbol=symbol,
            instrument_type=asset_type,
            side=side,
            quantity=quantity,
            requested_price=price,
            status=OrderStatus.PENDING
        )
        self.db.add(order)
        self.db.flush()

        tx_cost = self.tx_calculator.calculate_cost(side, quantity, price, asset_type)
        total_value = quantity * price

        holding = self.db.query(PaperHolding).filter(
            PaperHolding.paper_account_id == self.account_id,
            PaperHolding.symbol == symbol
        ).first()

        if side == OrderSide.BUY:
            total_cost = total_value + tx_cost
            if acc.available_cash < total_cost:
                order.status = OrderStatus.REJECTED
                order.reject_reason = "Insufficient cash"
            else:
                acc.available_cash -= total_cost
                order.status = OrderStatus.FILLED
                order.executed_price = price
                order.executed_at = datetime.now(timezone.utc)
                
                if holding:
                    total_qty = holding.quantity + quantity
                    total_cost_basis = (holding.quantity * holding.average_price) + (quantity * price)
                    holding.average_price = total_cost_basis / total_qty
                    holding.quantity = total_qty
                else:
                    holding = PaperHolding(
                        paper_account_id=self.account_id,
                        symbol=symbol,
                        instrument_type=asset_type,
                        quantity=quantity,
                        average_price=price
                    )
                    self.db.add(holding)

        elif side == OrderSide.SELL:
            if not holding or holding.quantity < quantity:
                order.status = OrderStatus.REJECTED
                order.reject_reason = "Insufficient holding quantity"
            else:
                total_proceeds = total_value - tx_cost
                acc.available_cash += total_proceeds
                order.status = OrderStatus.FILLED
                order.executed_price = price
                order.executed_at = datetime.now(timezone.utc)
                
                holding.quantity -= quantity
                if holding.quantity == 0:
                    self.db.delete(holding)

        self.db.commit()
        return order

    def place_buy_order(self, client_order_id: str, symbol: str, quantity: float, price: float, asset_type: AssetType) -> Any:
        return self._process_order(client_order_id, symbol, quantity, price, asset_type, OrderSide.BUY)

    def place_sell_order(self, client_order_id: str, symbol: str, quantity: float, price: float, asset_type: AssetType) -> Any:
        return self._process_order(client_order_id, symbol, quantity, price, asset_type, OrderSide.SELL)

    def cancel_order(self, client_order_id: str) -> bool:
        order = self.get_order(client_order_id)
        if not order:
            return False
        if order.status == OrderStatus.PENDING:
            order.status = OrderStatus.CANCELLED
            self.db.commit()
            return True
        return False
