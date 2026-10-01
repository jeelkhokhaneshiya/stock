from decimal import Decimal

CASH_TOLERANCE = Decimal("0.01")
PRICE_TOLERANCE = Decimal("0.01")
MARKET_VALUE_TOLERANCE = Decimal("1.0")

def check_cash(broker_cash: Decimal, internal_cash: Decimal):
    diff = broker_cash - internal_cash
    if abs(diff) <= CASH_TOLERANCE:
        return True, Decimal("0.0")
    return False, diff

def check_price(broker_price: Decimal, internal_price: Decimal):
    diff = broker_price - internal_price
    if abs(diff) <= PRICE_TOLERANCE:
        return True, Decimal("0.0")
    return False, diff
