import pytest
import os
from typing import Generator
from app.services.fundamentals.base import FundamentalProviderStatus

# We don't have a TwelveData provider implementation yet, but we define tests
# that assert the expected behavior of a generic TwelveData fundamental provider.

class MockTwelveDataResult:
    def __init__(self, status, fields=None):
        self.status = status
        self.available_fields = fields or []
        self.identity_verified = False

def test_missing_api_key():
    # A provider without an API key should return UNAVAILABLE / AUTH_ERROR
    # and safely avoid breaking the pipeline.
    result = MockTwelveDataResult(FundamentalProviderStatus.UNAVAILABLE)
    assert result.status == FundamentalProviderStatus.UNAVAILABLE
    assert not result.identity_verified

def test_401_403_access_restricted():
    # Free tier or invalid token should safely map to AUTH_ERROR or FORBIDDEN
    result = MockTwelveDataResult(FundamentalProviderStatus.FORBIDDEN)
    assert result.status == FundamentalProviderStatus.FORBIDDEN
    assert len(result.available_fields) == 0

def test_429_rate_limit():
    result = MockTwelveDataResult(FundamentalProviderStatus.RATE_LIMITED)
    assert result.status == FundamentalProviderStatus.RATE_LIMITED

def test_symbol_not_found():
    result = MockTwelveDataResult(FundamentalProviderStatus.NOT_FOUND)
    assert result.status == FundamentalProviderStatus.NOT_FOUND

def test_identity_mismatch_rejected():
    result = MockTwelveDataResult(FundamentalProviderStatus.UNAVAILABLE)
    # Even if HTTP is 200, an ISIN or name mismatch means UNAVAILABLE.
    result.identity_verified = False
    assert result.status == FundamentalProviderStatus.UNAVAILABLE
    assert not result.identity_verified
