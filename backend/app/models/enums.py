from enum import Enum

class AssetType(str, Enum):
    STOCK = "STOCK"
    ETF = "ETF"
    MUTUAL_FUND = "MUTUAL_FUND"
    INDEX_FUND = "INDEX_FUND"
    OTHER = "OTHER"

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

class ExecutionIntent(str, Enum):
    DELIVERY_LONG_TERM = "DELIVERY_LONG_TERM"
    INTRADAY = "INTRADAY"
    MIS = "MIS"
    MTF = "MTF"
    MARGIN = "MARGIN"
    LEVERAGE = "LEVERAGE"
    SHORT = "SHORT"

class ExecutionStatus(str, Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"

class DecisionAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    ADD = "ADD"
    REDUCE = "REDUCE"
    AVOID = "AVOID"

class CycleStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"

class ReconciliationStatus(str, Enum):
    MATCHED = "MATCHED"
    MISMATCH = "MISMATCH"
    BROKER_ONLY = "BROKER_ONLY"
    INTERNAL_ONLY = "INTERNAL_ONLY"
    ERROR = "ERROR"

class ReconciliationSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

class BrokerOrderStatus(str, Enum):
    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"

class ExecutionMode(str, Enum):
    PAPER = "PAPER"
    SHADOW = "SHADOW"
    LIVE = "LIVE"
