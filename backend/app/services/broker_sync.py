import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.schemas.broker import BrokerSnapshot, BrokerHealthStatus
from app.services.brokers.angel_one import AngelOneAuth, AngelOneClient, AngelOneAdapter
from app.services.paper_broker import PaperBroker

logger = logging.getLogger(__name__)

class BrokerSyncService:
    def __init__(self, db: Session, user_id: int, portfolio_id: str):
        self.db = db
        self.user_id = user_id
        self.portfolio_id = portfolio_id
        self.provider = settings.BROKER_PROVIDER.lower()
        self.adapter = self._initialize_adapter()

    def _initialize_adapter(self):
        if self.provider == "angel_one":
            auth = AngelOneAuth(
                api_key=settings.ANGEL_ONE_API_KEY or "",
                client_id=settings.ANGEL_ONE_CLIENT_ID or "",
                password=settings.ANGEL_ONE_PASSWORD or "",
                totp_secret=settings.ANGEL_ONE_TOTP_SECRET or ""
            )
            client = AngelOneClient(auth)
            return AngelOneAdapter(client)
        else:
            # Fallback to PaperBroker adapter pattern
            # For read-only sync, PaperBroker adapter needs a mapped interface
            # Since PaperBroker already operates internally, we wrap it
            from app.models.paper import PaperAccount
            account = self.db.query(PaperAccount).filter(PaperAccount.portfolio_id == int(self.portfolio_id)).first()
            return PaperBrokerWrapper(self.db, account.id if account else 0)

    def get_status(self) -> BrokerHealthStatus:
        mode = "PAPER"
        if self.provider == "angel_one" and settings.ENABLE_LIVE_TRADING:
            mode = "LIVE"
        elif self.provider == "angel_one":
            mode = "PAPER" # Since live is disabled, we consider it disabled/paper mode functionally or just report PAPER

        # The prompt says: "For Phase 9.1 the application must report: LIVE = DISABLED"
        # Let's use "DISABLED" if it's angel_one but live is false.
        if self.provider == "angel_one":
            mode = "DISABLED"

        status = BrokerHealthStatus(
            provider=self.provider,
            authenticated=False,
            reachable=False,
            mode=mode
        )

        try:
            auth_success = self.adapter.authenticate()
            status.authenticated = auth_success
            status.reachable = True
            status.last_successful_sync = datetime.now()
        except Exception as e:
            logger.error("Broker authentication failed during status check")
            status.last_error = "Authentication or network error"
            
        return status

    def get_snapshot(self) -> BrokerSnapshot:
        if not self.adapter.authenticate():
            raise ValueError("Failed to authenticate with broker")
            
        cash = self.adapter.get_available_cash()
        holdings = self.adapter.get_holdings()
        positions = self.adapter.get_positions()
        orders = self.adapter.get_orders()
        
        # Filter holdings strictly for DELIVERY as per rules
        filtered_holdings = []
        for h in holdings:
            if h.product.upper() == "DELIVERY" or self.provider == "paper":
                filtered_holdings.append(h)
                
        return BrokerSnapshot(
            cash=cash,
            holdings=filtered_holdings,
            positions=positions,
            orders=orders,
            timestamp=datetime.now()
        )

# Simple wrapper for PaperBroker to match interface
class PaperBrokerWrapper:
    def __init__(self, db: Session, account_id: int):
        self.paper = PaperBroker(db, account_id)
        
    def authenticate(self) -> bool:
        return True
        
    def get_available_cash(self):
        from app.schemas.broker import BrokerBalance
        from decimal import Decimal
        acc = self.paper._get_account()
        return BrokerBalance(
            available_cash=Decimal(str(acc.available_cash)),
            used_cash=Decimal(str(acc.initial_cash - acc.available_cash)),
            total_cash=Decimal(str(acc.initial_cash)),
            broker="PAPER"
        )
        
    def get_holdings(self):
        from app.schemas.broker import BrokerHolding
        from decimal import Decimal
        holdings = []
        for h in self.paper.get_holdings():
            holdings.append(BrokerHolding(
                broker="PAPER",
                symbol=h.symbol,
                exchange="PAPER",
                quantity=Decimal(str(h.quantity)),
                average_price=Decimal(str(h.average_price)),
                product="DELIVERY"
            ))
        return holdings
        
    def get_positions(self):
        return []
        
    def get_orders(self):
        return []
