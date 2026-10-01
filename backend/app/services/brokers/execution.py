from abc import ABC, abstractmethod
from typing import Optional
from app.schemas.broker import BrokerOrderRequest, BrokerOrderResponse

class BrokerExecutionAdapter(ABC):
    @abstractmethod
    def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderResponse:
        pass
        
    @abstractmethod
    def get_order_status(self, broker_order_id: str) -> BrokerOrderResponse:
        pass
        
    @abstractmethod
    def get_order(self, broker_order_id: str) -> BrokerOrderResponse:
        pass
        
    @abstractmethod
    def cancel_order(self, broker_order_id: str) -> BrokerOrderResponse:
        pass
        
    @abstractmethod
    def modify_order(self, broker_order_id: str, quantity: Optional[float] = None, price: Optional[float] = None) -> BrokerOrderResponse:
        pass
