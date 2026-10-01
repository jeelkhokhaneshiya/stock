from typing import Dict, Any, List
from decimal import Decimal
from datetime import datetime
from app.schemas.broker import BrokerHolding, BrokerBalance, BrokerOrder

class AngelOneMapper:
    @staticmethod
    def to_decimal(val: Any) -> Decimal:
        if val is None or val == "":
            return Decimal("0.0")
        try:
            return Decimal(str(val))
        except:
            return Decimal("0.0")

    @staticmethod
    def map_holdings(raw_data: List[Dict[str, Any]]) -> List[BrokerHolding]:
        if not raw_data:
            return []
            
        holdings = []
        for h in raw_data:
            # AngelOne returns 'product' as DELIVERY, INTRADAY, MARGIN
            # We strictly recognize DELIVERY
            holdings.append(
                BrokerHolding(
                    broker="ANGEL_ONE",
                    symbol=h.get("tradingsymbol", ""),
                    exchange=h.get("exchange", ""),
                    isin=h.get("isin", ""),
                    symbol_token=str(h.get("symboltoken", "")),
                    quantity=AngelOneMapper.to_decimal(h.get("quantity")),
                    average_price=AngelOneMapper.to_decimal(h.get("averageprice")),
                    last_price=AngelOneMapper.to_decimal(h.get("ltp")),
                    market_value=AngelOneMapper.to_decimal(h.get("marketvalue")),
                    profit_loss=AngelOneMapper.to_decimal(h.get("pnlpercentage")), # actually pnl
                    profit_loss_percent=AngelOneMapper.to_decimal(h.get("pnlpercentage")),
                    product=h.get("product", ""),
                    t1_quantity=AngelOneMapper.to_decimal(h.get("t1quantity"))
                )
            )
        return holdings

    @staticmethod
    def map_balance(raw_data: Dict[str, Any]) -> BrokerBalance:
        return BrokerBalance(
            broker="ANGEL_ONE",
            available_cash=AngelOneMapper.to_decimal(raw_data.get("availablecash")),
            used_cash=AngelOneMapper.to_decimal(raw_data.get("utilisedmargin")),
            total_cash=AngelOneMapper.to_decimal(raw_data.get("netcashaval"))
        )

    @staticmethod
    def map_orders(raw_data: List[Dict[str, Any]]) -> List[BrokerOrder]:
        if not raw_data:
            return []
            
        orders = []
        for o in raw_data:
            try:
                # Update time format "20-Oct-2020 10:00:00" or similar
                dt_str = o.get("updatetime")
                dt = datetime.strptime(dt_str, "%d-%b-%Y %H:%M:%S") if dt_str else datetime.now()
            except:
                dt = datetime.now()
                
            orders.append(
                BrokerOrder(
                    broker_order_id=str(o.get("orderid", "")),
                    symbol=o.get("tradingsymbol", ""),
                    exchange=o.get("exchange", ""),
                    side=o.get("transactiontype", ""),
                    quantity=AngelOneMapper.to_decimal(o.get("quantity")),
                    price=AngelOneMapper.to_decimal(o.get("price")),
                    status=o.get("status", "UNKNOWN"),
                    product=o.get("producttype", ""),
                    order_type=o.get("ordertype", ""),
                    created_at=dt,
                    updated_at=dt
                )
            )
        return orders
