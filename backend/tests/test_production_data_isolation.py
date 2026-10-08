import pytest
import os
from app.services.market_data.factory import get_market_data_service
from app.core.config import settings

def test_production_blocks_mock_provider():
    # Setup conditions that simulate production where the provider is incorrectly set to mock
    original_env = settings.APP_ENV
    original_provider = settings.MARKET_DATA_PROVIDER
    
    settings.APP_ENV = "production"
    settings.MARKET_DATA_PROVIDER = "mock"
    
    try:
        with pytest.raises(RuntimeError) as excinfo:
            _ = get_market_data_service()
        
        assert "PRODUCTION ISOLATION" in str(excinfo.value)
        assert "Mock provider is explicitly disabled in production mode" in str(excinfo.value)
    finally:
        # Restore configuration to avoid breaking subsequent tests
        settings.APP_ENV = original_env
        settings.MARKET_DATA_PROVIDER = original_provider

def test_production_blocks_fallback_to_mock_on_uninitialized_angelone():
    # Setup conditions that simulate production where angel one is not yet logged in globally
    original_env = settings.APP_ENV
    original_provider = settings.MARKET_DATA_PROVIDER
    
    settings.APP_ENV = "production"
    settings.MARKET_DATA_PROVIDER = "angelone"
    
    from unittest.mock import patch
    try:
        with patch("app.api.deps._global_angel_one_client", None):
            with pytest.raises(RuntimeError) as excinfo:
                _ = get_market_data_service()
            
            assert "Angel One client not initialized" in str(excinfo.value)
    finally:
        # Restore configuration
        settings.APP_ENV = original_env
        settings.MARKET_DATA_PROVIDER = original_provider
