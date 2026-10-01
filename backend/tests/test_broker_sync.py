import pytest
from decimal import Decimal
from unittest.mock import Mock, patch
from app.services.broker_sync import BrokerSyncService
from app.core.config import settings

@pytest.fixture
def mock_angel_adapter(monkeypatch):
    with patch("app.services.broker_sync.AngelOneAdapter") as mock_adapter_class:
        mock_adapter = Mock()
        mock_adapter.authenticate.return_value = True
        mock_adapter.get_available_cash.return_value = {"available_cash": Decimal("1000"), "used_cash": Decimal("0"), "total_cash": Decimal("1000"), "currency": "INR", "broker": "ANGEL_ONE"}
        mock_adapter.get_positions.return_value = []
        mock_adapter.get_orders.return_value = []
        mock_adapter_class.return_value = mock_adapter
        yield mock_adapter

def test_sync_status_paper(db_session, test_portfolio, monkeypatch):
    monkeypatch.setattr(settings, "BROKER_PROVIDER", "paper")
    service = BrokerSyncService(db_session, test_portfolio.user_id, str(test_portfolio.id))
    status = service.get_status()
    assert status.provider == "paper"
    assert status.mode == "PAPER"
    assert status.authenticated is True

def test_sync_status_angel_one_disabled(db_session, test_portfolio, monkeypatch, mock_angel_adapter):
    monkeypatch.setattr(settings, "BROKER_PROVIDER", "angel_one")
    monkeypatch.setattr(settings, "ENABLE_LIVE_TRADING", False)
    service = BrokerSyncService(db_session, test_portfolio.user_id, str(test_portfolio.id))
    
    # We patch initialize adapter in sync service so we don't hit network
    service.adapter = mock_angel_adapter
    
    status = service.get_status()
    assert status.provider == "angel_one"
    assert status.mode == "DISABLED"
    assert status.authenticated is True

def test_sync_snapshot_filters_delivery(db_session, test_portfolio, monkeypatch, mock_angel_adapter):
    monkeypatch.setattr(settings, "BROKER_PROVIDER", "angel_one")
    service = BrokerSyncService(db_session, test_portfolio.user_id, str(test_portfolio.id))
    service.adapter = mock_angel_adapter
    
    from app.schemas.broker import BrokerHolding
    # Mock holdings with Intraday and Delivery
    mock_angel_adapter.get_holdings.return_value = [
        BrokerHolding(broker="ANGEL_ONE", symbol="A", exchange="NSE", quantity=Decimal("1"), average_price=Decimal("1"), product="DELIVERY"),
        BrokerHolding(broker="ANGEL_ONE", symbol="B", exchange="NSE", quantity=Decimal("1"), average_price=Decimal("1"), product="INTRADAY")
    ]
    
    snapshot = service.get_snapshot()
    assert len(snapshot.holdings) == 1
    assert snapshot.holdings[0].symbol == "A"

def test_paper_broker_wrapper_works(db_session, test_portfolio, monkeypatch):
    monkeypatch.setattr(settings, "BROKER_PROVIDER", "paper")
    
    from app.models.paper import PaperAccount, PaperHolding
    account = PaperAccount(portfolio_id=test_portfolio.id, available_cash=5000.0, initial_cash=5000.0)
    db_session.add(account)
    db_session.commit()
    
    service = BrokerSyncService(db_session, test_portfolio.user_id, str(test_portfolio.id))
    snapshot = service.get_snapshot()
    
    assert snapshot.cash.available_cash == Decimal("5000.0")
    assert snapshot.cash.broker == "PAPER"
