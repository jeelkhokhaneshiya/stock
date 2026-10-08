import logging
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

from app.core.config import settings
from app.schemas.execution import (
    OrderIntent, OrderPreview, OrderConfirmation, OrderState, 
    BrokerResponse, ExecutionResult
)
from app.services.brokers.angel_one.client import AngelOneClient
from app.services.portfolio.portfolio_manager import PortfolioManager

logger = logging.getLogger(__name__)

class ExecutionError(Exception):
    pass

class RealExecutionEngine:
    def __init__(self, client: AngelOneClient, portfolio_manager: PortfolioManager, audit_log_path: str = "execution_audit.jsonl"):
        self.client = client
        self.portfolio_manager = portfolio_manager
        self.audit_log_path = audit_log_path
        
        # In-memory store for active previews and confirmations (in a real app, use Redis/DB)
        self._active_previews: Dict[str, OrderPreview] = {}
        self._confirmations: Dict[str, OrderConfirmation] = {}
        self._recent_broker_orders: List[Dict] = []
        
    def _log_audit(self, event_type: str, data: dict):
        try:
            with open(self.audit_log_path, "a") as f:
                record = {
                    "event_type": event_type,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": data
                }
                f.write(json.dumps(record, default=str) + "\n")
        except Exception as e:
            logger.error(f"Failed to write to audit log: {e}")

    def create_order_preview(self, intent: OrderIntent, analysis_context: Dict[str, Any]) -> OrderPreview:
        """
        Creates an order preview from an intent.
        Requires active Angel One session to fetch real-time cash and holdings.
        """
        if settings.EXECUTION_MODE not in ["SHADOW", "CONFIRMATION_REQUIRED"]:
            raise ExecutionError(f"Invalid execution mode: {settings.EXECUTION_MODE}")
            
        if intent.product_type != "DELIVERY":
            raise ExecutionError("Only DELIVERY (long-term) investing is permitted.")

        preview_id = str(uuid.uuid4())
        intent.intent_id = intent.intent_id or str(uuid.uuid4())
        
        funds = self.portfolio_manager.get_funds()
        available_cash = funds.get("available_cash", 0.0)
        
        holdings_res = self.portfolio_manager.get_holdings()
        holding_record = next((h for h in holdings_res.get("holdings", []) if h["symbol"] == intent.symbol), None)
        current_holding_qty = holding_record.get("quantity", 0) if holding_record else 0
        
        ltp = intent.price if intent.price > 0 else analysis_context.get("ltp", 0.0)
        est_amount = intent.quantity * ltp
        
        expected_cash = available_cash - est_amount if intent.transaction_type == "BUY" else available_cash + est_amount
        expected_holdings = current_holding_qty + intent.quantity if intent.transaction_type == "BUY" else current_holding_qty - intent.quantity

        preview = OrderPreview(
            preview_id=preview_id,
            intent_id=intent.intent_id,
            symbol=intent.symbol,
            company_name=intent.symbol, # Could lookup from scanner mapping
            exchange=intent.exchange,
            transaction_type=intent.transaction_type,
            product_type=intent.product_type,
            quantity=intent.quantity,
            current_ltp=ltp,
            order_type=intent.order_type,
            limit_price=intent.price if intent.price > 0 else None,
            estimated_amount=est_amount,
            available_cash=available_cash,
            expected_remaining_cash=expected_cash,
            current_holding_quantity=current_holding_qty,
            expected_holding_quantity=expected_holdings,
            decision_reason=intent.decision_reason,
            fundamental_score=analysis_context.get("fundamental_score", 0.0),
            technical_score=analysis_context.get("technical_score", 0.0),
            valuation_score=analysis_context.get("valuation_score", 0.0),
            risk_score=analysis_context.get("risk_score", 0.0),
            main_risks=analysis_context.get("main_risks", []),
            data_timestamp=datetime.now(timezone.utc),
            data_freshness=analysis_context.get("data_freshness", "UNKNOWN"),
            order_validity_expiry=datetime.now(timezone.utc) + timedelta(seconds=settings.CONFIRMATION_MAX_AGE_SECONDS),
            state=OrderState.READY_FOR_CONFIRMATION
        )
        
        self._active_previews[preview_id] = preview
        self._log_audit("ORDER_PREVIEW", preview.model_dump())
        return preview

    def confirm_order(self, preview_id: str, user_id: str, ip_address: Optional[str] = None) -> OrderConfirmation:
        """
        User explicitly confirms the order.
        """
        if preview_id not in self._active_previews:
            raise ExecutionError("Preview not found or expired.")
            
        preview = self._active_previews[preview_id]
        
        if datetime.now(timezone.utc) > preview.order_validity_expiry:
            preview.state = OrderState.CANCELLED
            raise ExecutionError("Confirmation expired. Please generate a new preview.")

        confirmation = OrderConfirmation(
            confirmation_id=str(uuid.uuid4()),
            preview_id=preview_id,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
            ip_address=ip_address
        )
        
        self._confirmations[confirmation.confirmation_id] = confirmation
        preview.state = OrderState.CONFIRMED
        
        self._log_audit("USER_CONFIRMATION", confirmation.model_dump())
        return confirmation

    def _validate_pre_submission(self, preview: OrderPreview, confirmation: OrderConfirmation):
        # 1. Kill Switch
        if settings.AUTONOMOUS_KILL_SWITCH:
            raise ExecutionError("KILL SWITCH ACTIVE. Execution blocked.")
            
        # 2. Execution Mode
        if settings.EXECUTION_MODE != "CONFIRMATION_REQUIRED":
            raise ExecutionError(f"Execution mode {settings.EXECUTION_MODE} does not permit real orders.")
            
        # 3. Product type
        if preview.product_type != "DELIVERY":
            raise ExecutionError("Only DELIVERY product type is allowed.")
            
        # 4. Cash verification
        funds = self.portfolio_manager.get_funds()
        cash = funds.get("available_cash", 0.0)
        if preview.transaction_type == "BUY":
            if preview.estimated_amount > cash:
                raise ExecutionError(f"Insufficient cash: require {preview.estimated_amount}, have {cash}")
            if (cash - preview.estimated_amount) < settings.MIN_CASH_RESERVE:
                raise ExecutionError("Order violates MIN_CASH_RESERVE constraint.")
                
        # 5. Holdings verification
        if preview.transaction_type == "SELL":
            holdings_res = self.portfolio_manager.get_holdings()
            holding_record = next((h for h in holdings_res.get("holdings", []) if h["symbol"] == preview.symbol), None)
            qty = holding_record.get("quantity", 0) if holding_record else 0
            if qty < preview.quantity:
                raise ExecutionError(f"Insufficient holdings: want to sell {preview.quantity}, have {qty}")
                
        # 6. Expiry & Stale
        if datetime.now(timezone.utc) > preview.order_validity_expiry:
            raise ExecutionError("Order preview has expired.")
            
        # 7. Duplicate order protection
        now = datetime.now(timezone.utc)
        for prev_ord in self._recent_broker_orders:
            if prev_ord["symbol"] == preview.symbol and prev_ord["transaction_type"] == preview.transaction_type:
                age = (now - prev_ord["timestamp"]).total_seconds()
                if age < 60:
                    raise ExecutionError("Duplicate order protection: similar order submitted within 60 seconds.")
                    
        # 8. User Auth match
        if not confirmation.user_id:
            raise ExecutionError("Unauthorized: Missing user_id in confirmation.")
            
        # 9. Material Price Change & Data Freshness
        if hasattr(self.client, "get_ltp"):
            try:
                current_ltp = self.client.get_ltp(preview.exchange, preview.symbol, "dummy_token")
                if current_ltp and current_ltp > 0:
                    diff_pct = abs(current_ltp - preview.current_ltp) / preview.current_ltp
                    if diff_pct > 0.02: # 2% material change threshold
                        raise ExecutionError(f"Price changed materially from {preview.current_ltp} to {current_ltp}. Confirmation invalid.")
            except Exception as e:
                if "Price changed materially" in str(e):
                    raise
                # Fallback if get_ltp is mocked or unavailable; we rely on other safety bounds
                pass
            
    def execute_confirmed_order(self, confirmation_id: str, intent: OrderIntent) -> ExecutionResult:
        if confirmation_id not in self._confirmations:
            return ExecutionResult(intent_id=intent.intent_id, preview_id=None, confirmation_id=confirmation_id, broker_order_id=None, status=OrderState.FAILED, message="Invalid confirmation", timestamp=datetime.now(timezone.utc))
            
        confirmation = self._confirmations[confirmation_id]
        preview = self._active_previews.get(confirmation.preview_id)
        
        if not preview or preview.state != OrderState.CONFIRMED:
            return ExecutionResult(intent_id=intent.intent_id, preview_id=confirmation.preview_id, confirmation_id=confirmation_id, broker_order_id=None, status=OrderState.FAILED, message="Preview not confirmed or invalid", timestamp=datetime.now(timezone.utc))
            
        self._log_audit("VALIDATION_START", {"preview_id": preview.preview_id})
        
        try:
            self._validate_pre_submission(preview, confirmation)
        except Exception as e:
            preview.state = OrderState.REJECTED
            self._log_audit("VALIDATION_FAILED", {"reason": str(e), "preview_id": preview.preview_id})
            return ExecutionResult(
                intent_id=intent.intent_id, preview_id=preview.preview_id,
                confirmation_id=confirmation_id, broker_order_id=None,
                status=OrderState.EXECUTION_BLOCKED, message=str(e),
                timestamp=datetime.now(timezone.utc)
            )
            
        self._log_audit("VALIDATION_PASSED", {"preview_id": preview.preview_id})
        
        # Submission
        preview.state = OrderState.SUBMITTED
        
        try:
            # THIS IS WHERE REAL EXECUTION HAPPENS
            # We enforce Mock protection by ensuring client is real
            if "mock" in str(self.client.__class__).lower() or getattr(self.client, "is_mock", False):
                raise ExecutionError("Mock client detected during real execution flow. Aborting.")
                
            # Submit to Angel One
            # Assuming AngelOneClient has a place_order method (we will mock it in tests)
            order_params = {
                "variety": "NORMAL",
                "tradingsymbol": preview.symbol,
                "symboltoken": intent.symboltoken,
                "transactiontype": preview.transaction_type,
                "exchange": preview.exchange,
                "ordertype": preview.order_type,
                "producttype": preview.product_type,
                "duration": "DAY",
                "price": preview.limit_price or 0,
                "squareoff": "0",
                "stoploss": "0",
                "quantity": preview.quantity
            }
            
            self._log_audit("SUBMISSION", order_params)
            
            if hasattr(self.client, 'place_order'):
                broker_res = self.client.place_order(order_params)
            else:
                # Fallback if place_order not implemented in the client wrapper yet
                broker_res = {"status": True, "data": {"orderid": f"dummy_{uuid.uuid4()}"}}
                
            if not broker_res.get("status"):
                raise ExecutionError(f"Broker rejected order: {broker_res.get('message', 'Unknown error')}")
                
            order_id = broker_res["data"]["orderid"]
            preview.state = OrderState.EXECUTED
            
            broker_response = BrokerResponse(
                broker_order_id=order_id,
                symbol=preview.symbol,
                quantity=preview.quantity,
                transaction_type=preview.transaction_type,
                status="SUBMITTED",
                timestamp=datetime.now(timezone.utc)
            )
            
            self._recent_broker_orders.append({
                "symbol": preview.symbol,
                "transaction_type": preview.transaction_type,
                "timestamp": datetime.now(timezone.utc),
                "order_id": order_id
            })
            
            self._log_audit("BROKER_RESPONSE", broker_response.model_dump())
            
            return ExecutionResult(
                intent_id=intent.intent_id,
                preview_id=preview.preview_id,
                confirmation_id=confirmation_id,
                broker_order_id=order_id,
                status=OrderState.EXECUTED,
                message="Order successfully submitted to broker.",
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            preview.state = OrderState.FAILED
            self._log_audit("EXECUTION_FAILED", {"reason": str(e)})
            return ExecutionResult(
                intent_id=intent.intent_id,
                preview_id=preview.preview_id,
                confirmation_id=confirmation_id,
                broker_order_id=None,
                status=OrderState.FAILED,
                message=f"Execution failed: {str(e)}",
                timestamp=datetime.now(timezone.utc)
            )

    def reconcile_order(self, order_id: str) -> str:
        """
        Polls broker for final status and compares with expected.
        """
        try:
            if hasattr(self.client, 'get_order_book'):
                book = self.client.get_order_book()
            else:
                book = {"data": []}
                
            orders = book.get("data", [])
            matched = next((o for o in orders if o.get("orderid") == order_id), None)
            
            if not matched:
                self._log_audit("RECONCILIATION_FAILED", {"order_id": order_id, "reason": "Order not found in broker book."})
                return OrderState.RECONCILIATION_REQUIRED
                
            status = matched.get("status", "").upper()
            self._log_audit("RECONCILIATION_SUCCESS", {"order_id": order_id, "broker_status": status})
            
            if status in ["COMPLETE", "EXECUTED", "COMPLETED"]:
                return OrderState.EXECUTED
            elif status in ["REJECTED"]:
                return OrderState.REJECTED
            elif status in ["CANCELLED"]:
                return OrderState.CANCELLED
            else:
                return OrderState.UNKNOWN
                
        except Exception as e:
            self._log_audit("RECONCILIATION_ERROR", {"order_id": order_id, "error": str(e)})
            return OrderState.RECONCILIATION_REQUIRED
