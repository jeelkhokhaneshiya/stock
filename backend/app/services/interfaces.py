from abc import ABC, abstractmethod
from typing import Any, List, Optional
from datetime import datetime
from app.models.enums import AssetType, OrderSide

class TransactionCostCalculator(ABC):
    @abstractmethod
    def calculate_cost(self, side: OrderSide, quantity: float, price: float, asset_type: AssetType) -> float:
        pass

class BrokerAdapter(ABC):
    @abstractmethod
    def authenticate(self) -> bool:
        pass

    @abstractmethod
    def get_account_balance(self) -> float:
        pass

    @abstractmethod
    def get_available_cash(self) -> float:
        pass

    @abstractmethod
    def get_positions(self) -> List[Any]:
        pass

    @abstractmethod
    def get_holdings(self) -> List[Any]:
        pass

    @abstractmethod
    def get_quote(self, symbol: str) -> float:
        pass

    @abstractmethod
    def get_order(self, order_id: str) -> Any:
        pass

    @abstractmethod
    def get_orders(self) -> List[Any]:
        pass

    @abstractmethod
    def place_buy_order(self, client_order_id: str, symbol: str, quantity: float, price: float, asset_type: AssetType) -> Any:
        pass

    @abstractmethod
    def place_sell_order(self, client_order_id: str, symbol: str, quantity: float, price: float, asset_type: AssetType) -> Any:
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        pass

class MarketDataProvider(ABC):
    @abstractmethod
    def get_quote(self, symbol: str, exchange: str) -> Any:
        pass

    @abstractmethod
    def get_historical_data(self, symbol: str, exchange: str, timeframe: str, start_date: datetime, end_date: datetime) -> List[Any]:
        pass

    @abstractmethod
    def get_company_info(self, symbol: str, exchange: str) -> Any:
        pass

    @abstractmethod
    def get_fundamentals(self, symbol: str, exchange: str) -> Any:
        pass

    @abstractmethod
    def get_etf_info(self, symbol: str, exchange: str) -> Any:
        pass

    @abstractmethod
    def get_mutual_fund_info(self, identifier: str) -> Any:
        pass

class InvestmentAnalyzer:
    def analyze(self, asset):
        raise NotImplementedError

class RiskEngine:
    def evaluate_risk(self, portfolio):
        raise NotImplementedError

class InvestmentDecisionEngine:
    def decide(self, analysis):
        raise NotImplementedError
