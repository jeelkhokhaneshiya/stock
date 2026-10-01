from typing import List
from app.services.brokers.angel_one.client import AngelOneClient
from app.services.brokers.angel_one.mapper import AngelOneMapper
from app.schemas.broker import BrokerHolding, BrokerBalance, BrokerOrder
from app.services.brokers.guard import LiveBrokerExecutionGuard

class AngelOneAdapter:
    def __init__(self, client: AngelOneClient):
        self.client = client
        self.mapper = AngelOneMapper()

    def authenticate(self) -> bool:
        return self.client.authenticate()

    def get_available_cash(self) -> BrokerBalance:
        raw_rms = self.client.get_rms()
        return self.mapper.map_balance(raw_rms)

    def get_holdings(self) -> List[BrokerHolding]:
        raw_holdings = self.client.get_holdings()
        # Ensure we only return delivery holdings (or let the caller filter, but the prompt says:
        # "Any holding reported as intraday/margin/etc. must NOT be converted into a long-term investment automatically."
        # We map everything but caller or we can filter. Let's return all and sync service filters.
        return self.mapper.map_holdings(raw_holdings)

    def get_positions(self) -> List[dict]:
        raw = self.client.get_positions()
        return raw if isinstance(raw, list) else []

    def get_orders(self) -> List[BrokerOrder]:
        raw_orders = self.client.get_order_book()
        return self.mapper.map_orders(raw_orders)

    def place_order(self, *args, **kwargs):
        LiveBrokerExecutionGuard.verify_execution_allowed()
