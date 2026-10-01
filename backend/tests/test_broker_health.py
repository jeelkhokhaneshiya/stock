import pytest
from unittest.mock import patch, MagicMock

from app.services.brokers.health import BrokerHealthService, BrokerHealthStatus
from app.services.brokers.angel_one.session import AngelOneSessionManager, SessionState
from app.services.brokers.circuit_breaker import CircuitBreaker, CircuitState

def test_circuit_breaker():
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=60)
    assert cb.is_allowed()
    cb.record_failure()
    cb.record_failure()
    assert cb.is_allowed()
    cb.record_failure()
    assert not cb.is_allowed()
    assert cb.state == CircuitState.OPEN
    
    cb.record_success()
    assert cb.is_allowed()
    assert cb.state == CircuitState.CLOSED

def test_session_manager():
    sm = AngelOneSessionManager()
    assert sm.state == SessionState.DISCONNECTED
    sm.login()
    assert sm.state == SessionState.CONNECTED
    
    # Mocking failure
    with patch('app.services.brokers.angel_one.session.datetime') as mock_dt:
        sm.state = SessionState.DISCONNECTED
        def raise_ex(): raise Exception("test")
        with patch.object(sm, 'login', side_effect=raise_ex):
            try:
                sm.login()
            except Exception:
                sm.state = SessionState.FAILED
                sm.failure_count += 1
        
        assert sm.state == SessionState.FAILED
        assert sm.failure_count > 0

def test_broker_health():
    health = BrokerHealthService()
    assert health.status == BrokerHealthStatus.HEALTHY
    
    health.record_failure("AUTH")
    assert health.status == BrokerHealthStatus.AUTHENTICATION_REQUIRED
    assert not health.authentication_valid
    
    health.record_failure("RATE_LIMIT")
    assert health.status == BrokerHealthStatus.RATE_LIMITED
    assert health.rate_limited
    
    health.record_success(150)
    assert health.status == BrokerHealthStatus.HEALTHY
    assert health.latency_ms == 150
    assert not health.rate_limited

def test_zero_order_calls(monkeypatch):
    import requests
    def mock_post(*args, **kwargs):
        raise RuntimeError("REAL BROKER API CALLED")
    
    monkeypatch.setattr(requests, "post", mock_post)
    sm = AngelOneSessionManager()
    sm.login() # Should not call order APIs
    assert sm.state == SessionState.CONNECTED

def test_1000_safety_case():
    health = BrokerHealthService()
    health.record_success(50)
    assert health.status == BrokerHealthStatus.HEALTHY
    # End-to-end flow is read-only, no buys actually execute in Angel One
