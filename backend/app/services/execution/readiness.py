import logging
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.schemas.execution import OrderIntent

logger = logging.getLogger(__name__)

class ExecutionReadinessError(Exception):
    pass

class ExecutionReadinessLayer:
    def __init__(self, portfolio_manager, audit_log_path: str = "order_intent_audit.jsonl"):
        self.portfolio_manager = portfolio_manager
        self.audit_log_path = audit_log_path
        self._recent_intents: List[OrderIntent] = []
        
    def generate_intent(self, decision: Dict[str, Any]) -> OrderIntent:
        """
        Validates the decision and generates an ORDER_INTENT if all conditions are met.
        """
        self._validate_system_permissions()
        
        action = decision.get("decision")
        if action not in ["BUY", "BUY_MORE", "REDUCE", "SELL"]:
            raise ExecutionReadinessError(f"Decision {action} does not result in an order intent.")
            
        self._validate_decision_freshness(decision)
        self._validate_quantity_and_price(decision)
        
        # Get market data, token, etc from PortfolioManager / AngelOne
        symbol = decision.get("symbol")
        token = self._resolve_token(symbol)
        
        # We assume NSE for now, but could be dynamic
        exchange = "NSE"
        
        transaction_type = "BUY" if action in ["BUY", "BUY_MORE"] else "SELL"
        
        quantity = decision.get("quantity", 0)
        est_val = decision.get("estimated_investment", 0.0)
        reason = decision.get("reason", "")
        
        self._validate_funds_and_holdings(symbol, transaction_type, quantity, est_val)
        self._validate_portfolio_concentration(symbol, transaction_type, est_val)
        
        # Construct intent
        intent = OrderIntent(
            symbol=symbol,
            symboltoken=token,
            exchange=exchange,
            transaction_type=transaction_type,
            product_type="DELIVERY",
            order_type="MARKET",
            quantity=quantity,
            price=0.0, # Market order
            estimated_value=est_val,
            decision_reason=reason,
            timestamp=datetime.now(timezone.utc)
        )
        
        self._validate_duplicate_order(intent)
        self._enforce_rate_limit()
        
        self._log_intent(intent)
        self._recent_intents.append(intent)
        
        # Trim recent intents
        if len(self._recent_intents) > 100:
            self._recent_intents.pop(0)
            
        return intent
        
    def _validate_system_permissions(self):
        if settings.AUTONOMOUS_KILL_SWITCH:
            raise ExecutionReadinessError("Kill switch is active. Execution disabled.")
        if settings.EXECUTION_MODE not in ["SHADOW", "CONFIRMATION_REQUIRED"]:
            raise ExecutionReadinessError(f"Safety configuration violated! Invalid execution mode: {settings.EXECUTION_MODE}")
        # Intents are just plans, they are allowed in SHADOW and CONFIRMATION_REQUIRED.
        # Real execution is blocked at the RealExecutionEngine layer.
    def _validate_decision_freshness(self, decision: Dict[str, Any]):
        dt = decision.get("timestamp")
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        age = (datetime.now(timezone.utc) - dt).total_seconds()
        if age > settings.DECISION_MAX_AGE_SECONDS:
            raise ExecutionReadinessError(f"Decision is too old ({age}s > {settings.DECISION_MAX_AGE_SECONDS}s)")

    def _validate_quantity_and_price(self, decision: Dict[str, Any]):
        if decision.get("quantity", 0) <= 0:
            raise ExecutionReadinessError("Invalid quantity: must be > 0")
        if decision.get("estimated_investment", 0) <= 0:
            raise ExecutionReadinessError("Invalid estimated value: must be > 0")

    def _resolve_token(self, symbol: str) -> str:
        # Ask portfolio manager's data service for the token
        token = self.portfolio_manager.client.get_token_for_symbol(symbol)
        if not token:
            raise ExecutionReadinessError(f"Could not resolve Angel One token for {symbol}")
        return token

    def _validate_funds_and_holdings(self, symbol: str, transaction_type: str, quantity: int, estimated_value: float):
        if transaction_type == "BUY":
            funds = self.portfolio_manager.get_funds()
            cash = funds.get("available_cash", 0.0)
            if estimated_value > cash:
                raise ExecutionReadinessError(f"Insufficient funds: required {estimated_value}, available {cash}")
        else: # SELL
            holdings = self.portfolio_manager.get_holdings()
            holding_record = next((h for h in holdings.get("holdings", []) if h["symbol"] == symbol), None)
            if not holding_record:
                raise ExecutionReadinessError(f"Cannot sell {symbol}: no holdings found.")
            available_qty = holding_record.get("quantity", 0)
            if quantity > available_qty:
                raise ExecutionReadinessError(f"Insufficient holdings: want to sell {quantity}, have {available_qty}")

    def _validate_portfolio_concentration(self, symbol: str, transaction_type: str, estimated_value: float):
        if transaction_type == "BUY":
            # Just a simple check against max single order amount for now
            if estimated_value > settings.MAX_SINGLE_ORDER_AMOUNT:
                raise ExecutionReadinessError(f"Order value {estimated_value} exceeds MAX_SINGLE_ORDER_AMOUNT {settings.MAX_SINGLE_ORDER_AMOUNT}")

    def _validate_duplicate_order(self, intent: OrderIntent):
        # Look for identical intents in the last 60 seconds
        recent_threshold = 60
        now = datetime.now(timezone.utc)
        for prev in self._recent_intents:
            if prev.symbol == intent.symbol and prev.transaction_type == intent.transaction_type:
                age = (now - prev.timestamp).total_seconds()
                if age < recent_threshold:
                    raise ExecutionReadinessError(f"Duplicate order protection: identical {intent.transaction_type} intent for {intent.symbol} generated {age:.1f}s ago")

    def _enforce_rate_limit(self):
        # Very simple rate limit (e.g. max 1 order per second locally)
        if not self._recent_intents:
            return
        last_intent = self._recent_intents[-1]
        age = (datetime.now(timezone.utc) - last_intent.timestamp).total_seconds()
        if age < 1.0: # 1 second delay
            raise ExecutionReadinessError("Rate limit exceeded: Please wait before generating another intent.")

    def _log_intent(self, intent: OrderIntent):
        try:
            with open(self.audit_log_path, "a") as f:
                # Need to serialize datetime properly
                intent_dict = intent.model_dump()
                intent_dict["timestamp"] = intent_dict["timestamp"].isoformat()
                f.write(json.dumps(intent_dict) + "\n")
            logger.info(f"Generated ORDER_INTENT for {intent.symbol} ({intent.transaction_type} {intent.quantity})")
        except Exception as e:
            logger.error(f"Failed to log order intent: {e}")
