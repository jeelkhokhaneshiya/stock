from typing import Optional, Dict
from decimal import Decimal
import uuid
from app.services.brokers.execution import BrokerExecutionAdapter
from app.schemas.broker import BrokerOrderRequest, BrokerOrderResponse
from app.models.enums import BrokerOrderStatus

class MockAngelOneExecutionAdapter(BrokerExecutionAdapter):
    """
    Mock execution adapter strictly for Phase 9.3 testing.
    Never calls actual Angel One.
    """
    def __init__(self):
        self.orders: Dict[str, BrokerOrderResponse] = {}
        # Allows tests to control the simulated behavior
        self.simulation_mode = "SUCCESS" 
        self.partial_fill_amount = Decimal("0")

    def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderResponse:
        if request.client_order_id in [o.client_order_id for o in self.orders.values()]:
            # Simulate rejection if duplicate? In reality, idempotency is at service layer.
            # But adapter might return error. Let's just create a new one to simulate broker behavior if they didn't catch it,
            # or return existing if we map it. Actually, service layer should block it.
            pass
            
        broker_order_id = f"MOCK-{uuid.uuid4().hex[:8].upper()}"
        
        status = BrokerOrderStatus.SUBMITTED
        executed = Decimal("0")
        remaining = request.quantity
        price = None
        error_code = None
        error_message = None
        
        if self.simulation_mode == "SUCCESS":
            status = BrokerOrderStatus.OPEN
        elif self.simulation_mode == "REJECTED":
            status = BrokerOrderStatus.REJECTED
            error_code = "MOCK_REJECT"
            error_message = "Mock rejection"
        elif self.simulation_mode == "TIMEOUT":
            status = BrokerOrderStatus.UNKNOWN
        elif self.simulation_mode == "PARTIAL_FILL":
            status = BrokerOrderStatus.PARTIALLY_FILLED
            executed = self.partial_fill_amount
            remaining = request.quantity - executed
            price = request.price or Decimal("100.0")
        elif self.simulation_mode == "FAILED":
            status = BrokerOrderStatus.FAILED
            error_code = "MOCK_FAIL"
        
        response = BrokerOrderResponse(
            broker_order_id=broker_order_id,
            client_order_id=request.client_order_id,
            status=status,
            executed_quantity=executed,
            remaining_quantity=remaining,
            average_fill_price=price,
            error_code=error_code,
            error_message=error_message
        )
        self.orders[broker_order_id] = response
        return response

    def get_order_status(self, broker_order_id: str) -> BrokerOrderResponse:
        return self.get_order(broker_order_id)

    def get_order(self, broker_order_id: str) -> BrokerOrderResponse:
        if broker_order_id not in self.orders:
            raise ValueError("Order not found in mock")
        return self.orders[broker_order_id]

    def cancel_order(self, broker_order_id: str) -> BrokerOrderResponse:
        order = self.get_order(broker_order_id)
        if order.status in [BrokerOrderStatus.FILLED, BrokerOrderStatus.REJECTED, BrokerOrderStatus.CANCELLED]:
            raise ValueError("Cannot cancel terminal order")
            
        order.status = BrokerOrderStatus.CANCELLED
        return order

    def modify_order(self, broker_order_id: str, quantity: Optional[float] = None, price: Optional[float] = None) -> BrokerOrderResponse:
        order = self.get_order(broker_order_id)
        # Mock modification
        return order
