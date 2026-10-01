import logging
from typing import List, Dict, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session
from datetime import datetime
from app.schemas.reconciliation import (
    ReconciliationReport, ReconciliationItemSchema, 
    CashReconciliation, HoldingsReconciliation
)
from app.models.enums import ReconciliationStatus, ReconciliationSeverity
from app.models.reconciliation import ReconciliationRun, ReconciliationItem
from app.services.broker_sync import BrokerSyncService
from app.models.paper import PaperAccount, PaperHolding
from app.services.reconciliation.rules import check_cash, check_price

logger = logging.getLogger(__name__)

class ReconciliationService:
    def __init__(self, db: Session, user_id: int, portfolio_id: str):
        self.db = db
        self.user_id = user_id
        self.portfolio_id = portfolio_id
        self.sync_service = BrokerSyncService(db, user_id, portfolio_id)
        
    def _get_internal_account(self) -> PaperAccount:
        account = self.db.query(PaperAccount).filter(PaperAccount.portfolio_id == int(self.portfolio_id)).first()
        if not account:
            raise ValueError("Portfolio account not found")
        return account
        
    def _match_holdings(self, broker_holdings: List, internal_holdings: List) -> Tuple[Dict, List, List]:
        # Returns matched (tuple: broker, internal), broker_only, internal_only
        matched = {}
        broker_only = []
        
        # Group internal by symbol for easy lookup
        internal_map = {h.symbol.upper(): h for h in internal_holdings}
        
        for bh in broker_holdings:
            matched_internal = None
            if bh.symbol.upper() in internal_map:
                matched_internal = internal_map.pop(bh.symbol.upper())
                
            if matched_internal:
                matched[bh.symbol] = (bh, matched_internal)
            else:
                broker_only.append(bh)
                
        internal_only = list(internal_map.values())
        return matched, broker_only, internal_only

    def run_reconciliation(self) -> ReconciliationReport:
        broker_snapshot = self.sync_service.get_snapshot()
        internal_account = self._get_internal_account()
        
        items: List[ReconciliationItemSchema] = []
        run_status = ReconciliationStatus.MATCHED
        
        # 1. Check Cash
        cash_match, cash_diff = check_cash(
            broker_snapshot.cash.available_cash, 
            Decimal(str(internal_account.available_cash))
        )
        
        if not cash_match:
            run_status = ReconciliationStatus.MISMATCH
            
        cash_recon = CashReconciliation(
            broker_cash=broker_snapshot.cash.available_cash,
            internal_cash=Decimal(str(internal_account.available_cash)),
            cash_difference=cash_diff
        )
        
        # 2. Check unsupported positions from broker snapshot?
        # The BrokerSyncService filters them out from holdings, BUT wait, the requirements say:
        # "If broker reports INTRADAY... Report them separately as: UNSUPPORTED_BROKER_POSITION with severity = CRITICAL"
        # We need raw holdings from adapter to detect this.
        raw_holdings = self.sync_service.adapter.get_holdings()
        valid_broker_holdings = []
        for rh in raw_holdings:
            if rh.product.upper() != "DELIVERY" and self.sync_service.provider != "paper":
                items.append(ReconciliationItemSchema(
                    symbol=rh.symbol,
                    isin=rh.isin,
                    exchange=rh.exchange,
                    broker_quantity=rh.quantity,
                    status=ReconciliationStatus.ERROR,
                    severity=ReconciliationSeverity.CRITICAL,
                    reason="UNSUPPORTED_BROKER_POSITION"
                ))
                run_status = ReconciliationStatus.MISMATCH
            else:
                valid_broker_holdings.append(rh)
                
        # 3. Match holdings
        internal_holdings = internal_account.holdings
        matched, broker_only, internal_only = self._match_holdings(valid_broker_holdings, internal_holdings)
        
        for symbol, (bh, ih) in matched.items():
            iqty = Decimal(str(ih.quantity))
            bqty = bh.quantity
            qty_diff = bqty - iqty
            
            iprice = Decimal(str(ih.average_price))
            bprice = bh.average_price
            price_match, price_diff = check_price(bprice, iprice)
            
            item_status = ReconciliationStatus.MATCHED
            severity = ReconciliationSeverity.INFO
            reason = []
            
            if qty_diff != 0:
                item_status = ReconciliationStatus.MISMATCH
                severity = ReconciliationSeverity.WARNING
                reason.append(f"Quantity mismatch ({qty_diff:+.2f})")
                
            if not price_match:
                item_status = ReconciliationStatus.MISMATCH
                severity = ReconciliationSeverity.WARNING if severity != ReconciliationSeverity.CRITICAL else severity
                reason.append(f"Price mismatch ({price_diff:+.2f})")
                
            if item_status != ReconciliationStatus.MATCHED:
                run_status = ReconciliationStatus.MISMATCH
                
            items.append(ReconciliationItemSchema(
                symbol=symbol,
                isin=bh.isin,
                exchange=bh.exchange,
                broker_quantity=bqty,
                internal_quantity=iqty,
                quantity_difference=qty_diff,
                broker_average_price=bprice,
                internal_average_price=iprice,
                average_price_difference=price_diff,
                status=item_status,
                severity=severity,
                reason="; ".join(reason) if reason else None
            ))
            
        for bh in broker_only:
            run_status = ReconciliationStatus.MISMATCH
            items.append(ReconciliationItemSchema(
                symbol=bh.symbol,
                isin=bh.isin,
                exchange=bh.exchange,
                broker_quantity=bh.quantity,
                internal_quantity=Decimal("0"),
                quantity_difference=bh.quantity,
                broker_average_price=bh.average_price,
                internal_average_price=Decimal("0"),
                status=ReconciliationStatus.BROKER_ONLY,
                severity=ReconciliationSeverity.WARNING,
                reason="Broker only holding"
            ))
            
        for ih in internal_only:
            run_status = ReconciliationStatus.MISMATCH
            items.append(ReconciliationItemSchema(
                symbol=ih.symbol,
                broker_quantity=Decimal("0"),
                internal_quantity=Decimal(str(ih.quantity)),
                quantity_difference=Decimal(str(-ih.quantity)),
                broker_average_price=Decimal("0"),
                internal_average_price=Decimal(str(ih.average_price)),
                status=ReconciliationStatus.INTERNAL_ONLY,
                severity=ReconciliationSeverity.CRITICAL,
                reason="Internal only holding (liquidation risk)"
            ))

        holdings_recon = HoldingsReconciliation(
            matched_count=len(matched),
            mismatch_count=len([i for i in items if i.status == ReconciliationStatus.MISMATCH]),
            broker_only_count=len(broker_only),
            internal_only_count=len(internal_only)
        )
        
        # Save to DB
        run = ReconciliationRun(
            portfolio_id=int(self.portfolio_id),
            broker=broker_snapshot.cash.broker,
            status=run_status
        )
        self.db.add(run)
        self.db.flush() # to get run.id
        
        for item in items:
            db_item = ReconciliationItem(
                run_id=run.id,
                status=item.status,
                severity=item.severity,
                symbol=item.symbol,
                isin=item.isin,
                exchange=item.exchange,
                broker_quantity=item.broker_quantity,
                internal_quantity=item.internal_quantity,
                quantity_difference=item.quantity_difference,
                broker_average_price=item.broker_average_price,
                internal_average_price=item.internal_average_price,
                price_difference=item.average_price_difference,
                reason=item.reason
            )
            self.db.add(db_item)
            
        self.db.commit()
        
        report = ReconciliationReport(
            reconciliation_id=run.id,
            portfolio_id=int(self.portfolio_id),
            broker=run.broker,
            status=run.status,
            generated_at=run.created_at,
            cash=cash_recon,
            holdings=holdings_recon,
            items=items,
            summary=f"Reconciliation completed with status {run.status.name}"
        )
        return report
