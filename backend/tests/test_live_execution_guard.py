import pytest
from app.services.brokers.guard import LiveBrokerExecutionGuard
from app.core.config import settings

def test_live_execution_guard_disabled(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LIVE_TRADING", False)
    with pytest.raises(ValueError, match="LIVE_TRADING_DISABLED"):
        LiveBrokerExecutionGuard.verify_execution_allowed()

def test_live_execution_guard_enabled_but_phase_9_1(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LIVE_TRADING", True)
    # Phase 9.1 rule: ALWAYS reject
    with pytest.raises(ValueError, match="LIVE_TRADING_DISABLED"):
        LiveBrokerExecutionGuard.verify_execution_allowed()
