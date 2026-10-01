import pytest
from decimal import Decimal
from unittest.mock import Mock, patch
from app.models.enums import ReconciliationStatus, ReconciliationSeverity, AssetType
from app.services.reconciliation.service import ReconciliationService
from app.schemas.broker import BrokerHolding, BrokerBalance, BrokerSnapshot
from app.models.paper import PaperAccount, PaperHolding
from app.core.config import settings

@pytest.fixture
def mock_sync_service():
    with patch("app.services.reconciliation.service.BrokerSyncService") as mock:
        yield mock

def test_perfect_match(db_session, test_portfolio, monkeypatch, mock_sync_service):
    monkeypatch.setattr(settings, "BROKER_PROVIDER", "angel_one")
    
    acc = PaperAccount(portfolio_id=test_portfolio.id, available_cash=1000.0, initial_cash=1000.0)
    db_session.add(acc)
    db_session.commit()
    
    h = PaperHolding(paper_account_id=acc.id, symbol="TCS", instrument_type=AssetType.STOCK, quantity=10, average_price=3000.0)
    db_session.add(h)
    db_session.commit()
    
    mock_sync_instance = mock_sync_service.return_value
    mock_sync_instance.provider = "angel_one"
    
    # Needs to match internal holdings
    bh = BrokerHolding(
        broker="ANGEL_ONE", symbol="TCS", exchange="NSE", 
        quantity=Decimal("10"), average_price=Decimal("3000.0"), product="DELIVERY"
    )
    
    # Mock snapshot
    snap = BrokerSnapshot(
        cash=BrokerBalance(available_cash=Decimal("1000.0"), used_cash=Decimal("0"), total_cash=Decimal("1000.0"), broker="ANGEL_ONE"),
        holdings=[bh],
        orders=[],
        timestamp="2026-09-30T10:00:00Z"
    )
    mock_sync_instance.get_snapshot.return_value = snap
    
    # Adapter mock to avoid crash when fetching raw holdings (for unsupported detection)
    mock_adapter = Mock()
    mock_adapter.get_holdings.return_value = [bh]
    mock_sync_instance.adapter = mock_adapter

    service = ReconciliationService(db_session, test_portfolio.user_id, str(test_portfolio.id))
    report = service.run_reconciliation()
    
    assert report.status == ReconciliationStatus.MATCHED
    assert len(report.items) == 1
    assert report.items[0].status == ReconciliationStatus.MATCHED

def test_critical_safety_no_orders(db_session, test_portfolio, monkeypatch, mock_sync_service):
    monkeypatch.setattr(settings, "BROKER_PROVIDER", "angel_one")
    
    acc = PaperAccount(portfolio_id=test_portfolio.id, available_cash=1000.0, initial_cash=1000.0)
    db_session.add(acc)
    db_session.commit()
    
    h = PaperHolding(paper_account_id=acc.id, symbol="ABC", instrument_type=AssetType.STOCK, quantity=50, average_price=10.0)
    db_session.add(h)
    db_session.commit()
    
    mock_sync_instance = mock_sync_service.return_value
    mock_sync_instance.provider = "angel_one"
    
    bh = BrokerHolding(
        broker="ANGEL_ONE", symbol="ABC", exchange="NSE", 
        quantity=Decimal("100"), average_price=Decimal("10.0"), product="DELIVERY"
    )
    
    snap = BrokerSnapshot(
        cash=BrokerBalance(available_cash=Decimal("1000.0"), used_cash=Decimal("0"), total_cash=Decimal("1000.0"), broker="ANGEL_ONE"),
        holdings=[bh],
        orders=[],
        timestamp="2026-09-30T10:00:00Z"
    )
    mock_sync_instance.get_snapshot.return_value = snap
    
    mock_adapter = Mock()
    mock_adapter.get_holdings.return_value = [bh]
    mock_sync_instance.adapter = mock_adapter

    service = ReconciliationService(db_session, test_portfolio.user_id, str(test_portfolio.id))
    report = service.run_reconciliation()
    
    assert report.status == ReconciliationStatus.MISMATCH
    assert report.items[0].quantity_difference == Decimal("50")
    
    # Confirm no orders or db modifications happen to internal portfolio
    acc_after = db_session.query(PaperAccount).filter(PaperAccount.portfolio_id == test_portfolio.id).first()
    h_after = db_session.query(PaperHolding).filter(PaperHolding.paper_account_id == acc_after.id).first()
    assert h_after.quantity == 50  # NO AUTOMATIC TRADE OCCURRED

def test_critical_liquidation_test(db_session, test_portfolio, monkeypatch, mock_sync_service):
    monkeypatch.setattr(settings, "BROKER_PROVIDER", "angel_one")
    
    acc = PaperAccount(portfolio_id=test_portfolio.id, available_cash=1000.0, initial_cash=1000.0)
    db_session.add(acc)
    db_session.commit()
    
    h = PaperHolding(paper_account_id=acc.id, symbol="XYZ", instrument_type=AssetType.STOCK, quantity=100, average_price=10.0)
    db_session.add(h)
    db_session.commit()
    
    mock_sync_instance = mock_sync_service.return_value
    mock_sync_instance.provider = "angel_one"
    
    snap = BrokerSnapshot(
        cash=BrokerBalance(available_cash=Decimal("1000.0"), used_cash=Decimal("0"), total_cash=Decimal("1000.0"), broker="ANGEL_ONE"),
        holdings=[],
        orders=[],
        timestamp="2026-09-30T10:00:00Z"
    )
    mock_sync_instance.get_snapshot.return_value = snap
    
    mock_adapter = Mock()
    mock_adapter.get_holdings.return_value = []
    mock_sync_instance.adapter = mock_adapter

    service = ReconciliationService(db_session, test_portfolio.user_id, str(test_portfolio.id))
    report = service.run_reconciliation()
    
    assert report.status == ReconciliationStatus.MISMATCH
    assert report.items[0].status == ReconciliationStatus.INTERNAL_ONLY
    assert report.items[0].severity == ReconciliationSeverity.CRITICAL
    
    h_after = db_session.query(PaperHolding).filter(PaperHolding.paper_account_id == acc.id).first()
    assert h_after.quantity == 100  # NO AUTOMATIC LIQUIDATION OCCURRED

def test_unsupported_broker_position(db_session, test_portfolio, monkeypatch, mock_sync_service):
    monkeypatch.setattr(settings, "BROKER_PROVIDER", "angel_one")
    
    acc = PaperAccount(portfolio_id=test_portfolio.id, available_cash=1000.0, initial_cash=1000.0)
    db_session.add(acc)
    db_session.commit()
    
    mock_sync_instance = mock_sync_service.return_value
    mock_sync_instance.provider = "angel_one"
    
    bh_invalid = BrokerHolding(
        broker="ANGEL_ONE", symbol="FUT", exchange="NSE", 
        quantity=Decimal("100"), average_price=Decimal("10.0"), product="INTRADAY"
    )
    
    snap = BrokerSnapshot(
        cash=BrokerBalance(available_cash=Decimal("1000.0"), used_cash=Decimal("0"), total_cash=Decimal("1000.0"), broker="ANGEL_ONE"),
        holdings=[], # Sync service filters it out from snapshot
        orders=[],
        timestamp="2026-09-30T10:00:00Z"
    )
    mock_sync_instance.get_snapshot.return_value = snap
    
    mock_adapter = Mock()
    mock_adapter.get_holdings.return_value = [bh_invalid] # Raw adapter returns it
    mock_sync_instance.adapter = mock_adapter

    service = ReconciliationService(db_session, test_portfolio.user_id, str(test_portfolio.id))
    report = service.run_reconciliation()
    
    assert report.status == ReconciliationStatus.MISMATCH
    assert len(report.items) == 1
    assert report.items[0].status == ReconciliationStatus.ERROR
    assert report.items[0].severity == ReconciliationSeverity.CRITICAL
    assert report.items[0].reason == "UNSUPPORTED_BROKER_POSITION"
