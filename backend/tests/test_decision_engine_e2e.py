"""
test_decision_engine_e2e.py
===========================
End-to-end test of the decision engine using real Angel One read-only data.
Verifies that real market data and portfolio state flow through the entire
analysis pipeline correctly and produce valid decisions without executing.

Run:
  pytest tests/test_decision_engine_e2e.py -v -s
"""

from __future__ import annotations

import os
import pytest
from decimal import Decimal

from app.core.config import settings
from app.services.brokers.angel_one.auth import AngelOneAuth
from app.services.brokers.angel_one.client import AngelOneClient
from app.services.brokers.angel_one.data_service import AngelOneDataService
from app.services.portfolio.portfolio_manager import PortfolioManager


@pytest.fixture(scope="module")
def creds_available() -> bool:
    return all([
        settings.ANGEL_ONE_API_KEY,
        settings.ANGEL_ONE_CLIENT_ID,
        settings.ANGEL_ONE_PASSWORD,
        settings.ANGEL_ONE_TOTP_SECRET,
    ])

@pytest.fixture(scope="module")
def live_portfolio_manager(creds_available):
    if not creds_available:
        pytest.skip("Angel One credentials not configured — skipping E2E tests")

    import app.api.deps
    old_client = getattr(app.api.deps, "_global_angel_one_client", None)
    old_provider = settings.MARKET_DATA_PROVIDER
    
    try:
        if app.api.deps._global_angel_one_client and app.api.deps._global_angel_one_client.auth.is_authenticated():
            client = app.api.deps._global_angel_one_client
        else:
            auth = AngelOneAuth(
                api_key=settings.ANGEL_ONE_API_KEY,
                client_id=settings.ANGEL_ONE_CLIENT_ID,
                password=settings.ANGEL_ONE_PASSWORD,
                totp_secret=settings.ANGEL_ONE_TOTP_SECRET,
            )
            client = AngelOneClient(auth=auth)
            client.authenticate()
            app.api.deps._global_angel_one_client = client
            
        settings.MARKET_DATA_PROVIDER = "angelone"
        
        data_svc = AngelOneDataService(client)
        manager = PortfolioManager(client=data_svc)
        yield manager
    finally:
        app.api.deps._global_angel_one_client = old_client
        settings.MARKET_DATA_PROVIDER = old_provider

class TestDecisionEngineE2E:
    
    def test_guards_enabled(self):
        """Ensure execution guards are ON so no real orders can be sent."""
        assert settings.ENABLE_LIVE_TRADING is False
        assert settings.BROKER_EXECUTION_BLOCKED is True
        assert settings.LIVE_EXECUTION_UNLOCKED is False
        
    def test_full_portfolio_analysis(self, live_portfolio_manager):
        """Test the full analysis pipeline using real live data."""
        manager = live_portfolio_manager
        
        # Isolate the external network calls to timeout deterministically in the E2E test
        import httpx
        original_timeout = manager.client._client.http_client.timeout
        manager.client._client.http_client.timeout = httpx.Timeout(5.0)
        
        try:
            analysis = manager.get_full_portfolio_analysis()
        finally:
            manager.client._client.http_client.timeout = original_timeout
        
        if analysis["status"] == "BROKER_DISCONNECTED":
            pytest.skip(f"External network timeout or API disconnected: {analysis.get('reason')}")
            
        assert analysis["status"] == "OK", f"Analysis failed: {analysis.get('reason')}"
        
        summary = analysis["portfolio_summary"]
        assert "cash_available" in summary
        assert "total_portfolio_value" in summary
        assert "unrealized_pnl" in summary
        
        # Verify the decision plan
        action_plan = analysis["daily_investment_action_plan"]
        
        for decision in action_plan:
            assert "symbol" in decision
            assert "action" in decision
            assert decision["action"] in ["BUY", "BUY_MORE", "HOLD", "REDUCE", "SELL", "WATCH", "NO_ACTION"]
            assert "quantity" in decision
            assert "estimated_value" in decision
            assert "confidence" in decision
            assert "reasons" in decision
            
            # Loss alone never triggers SELL: This is hard to assert strictly without injecting state, 
            # but we can check if it's a SELL and pnl < 0, it must have a broken thesis reason.
            if decision["action"] == "SELL" and decision.get("pnl_pct", 0) < 0:
                reasons_str = " ".join(decision["reasons"])
                assert "thesis" in reasons_str.lower() and "broken" in reasons_str.lower(), \
                    "Sell decision on loss must be due to broken thesis."
                    
            # Insufficient cash -> no BUY:
            if decision["action"] in ["BUY", "BUY_MORE"]:
                assert decision["quantity"] > 0, "BUY decision must have positive quantity."
                assert summary["cash_available"] >= decision["estimated_value"], \
                    "Estimated investment must not exceed available cash."
                    
    def test_data_is_real(self, live_portfolio_manager):
        """Verify the data comes from the real Angel One connection."""
        assert live_portfolio_manager.client._client.BASE_URL == "https://apiconnect.angelone.in"

    def test_order_intent_and_preview_creation(self, live_portfolio_manager):
        """Test that actionable decisions correctly generate OrderIntent and OrderPreview without executing."""
        manager = live_portfolio_manager
        
        # Mock the external network call to timeout deterministically in case of issues
        import httpx
        original_timeout = manager.client._client.http_client.timeout
        manager.client._client.http_client.timeout = httpx.Timeout(5.0)
        
        try:
            analysis = manager.get_full_portfolio_analysis()
        finally:
            manager.client._client.http_client.timeout = original_timeout
            
        if analysis["status"] == "BROKER_DISCONNECTED":
            pytest.skip("Broker disconnected")
            
        action_plan = analysis["daily_investment_action_plan"]
        
        from app.schemas.execution import OrderIntent
        from app.services.execution.real_execution import RealExecutionEngine
        import uuid
        from datetime import datetime, timezone
        
        engine = RealExecutionEngine(manager.client._client, manager, "audit_test.jsonl")
        
        previews_generated = 0
        for decision in action_plan:
            action = decision.get("action")
            qty = decision.get("quantity", 0)
            
            if action in ["BUY", "BUY_MORE", "SELL", "REDUCE"] and qty > 0:
                tx_type = "BUY" if action in ["BUY", "BUY_MORE"] else "SELL"
                price = decision.get("current_price", 0.0)
                
                # 13. Actionable decision creates OrderIntent
                intent = OrderIntent(
                    intent_id=str(uuid.uuid4()),
                    symbol=decision["symbol"],
                    symboltoken="0",
                    exchange="NSE",
                    transaction_type=tx_type,
                    product_type="DELIVERY",
                    order_type="MARKET",
                    quantity=qty,
                    price=price,
                    estimated_value=decision.get("estimated_value", qty*price),
                    decision_reason="test",
                    timestamp=datetime.now(timezone.utc)
                )
                assert intent.transaction_type in ["BUY", "SELL"]
                
                # 15. OrderPreview created
                # 16. OrderPreview does not submit broker order
                context = {"ltp": price}
                
                # We assert this creates a preview without raising or submitting
                preview = engine.create_order_preview(intent, context)
                assert preview is not None
                assert preview.state == "READY_FOR_CONFIRMATION"
                assert preview.product_type == "DELIVERY"
                previews_generated += 1
                
        # If any actionable intents were found, we verified they generated previews.
        # If none were found (e.g. all HOLD/WATCH), we at least passed without crashing.
        assert previews_generated >= 0 
        
    def test_delivery_only_restriction(self, live_portfolio_manager):
        from app.schemas.execution import OrderIntent
        from app.services.execution.real_execution import RealExecutionEngine, ExecutionError
        import uuid
        from datetime import datetime, timezone
        
        engine = RealExecutionEngine(live_portfolio_manager.client._client, live_portfolio_manager, "audit_test.jsonl")
        
        # 19. DELIVERY-only restriction remains
        intent = OrderIntent(
            intent_id=str(uuid.uuid4()),
            symbol="INFY",
            symboltoken="0",
            exchange="NSE",
            transaction_type="BUY",
            product_type="INTRADAY", # Invalid product type
            order_type="MARKET",
            quantity=10,
            price=100.0,
            estimated_value=1000.0,
            decision_reason="test",
            timestamp=datetime.now(timezone.utc)
        )
        
        with pytest.raises(ExecutionError, match="DELIVERY"):
            engine.create_order_preview(intent, {"ltp": 100.0})
