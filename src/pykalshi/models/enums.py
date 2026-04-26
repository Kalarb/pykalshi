"""Enums for the Kalshi API."""

from enum import Enum


class Side(str, Enum):
    YES = "yes"
    NO = "no"


class Action(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    RESTING = "resting"
    CANCELED = "canceled"
    EXECUTED = "executed"


class OrderType(str, Enum):
    LIMIT = "limit"
    MARKET = "market"


class STPType(str, Enum):
    TAKER_AT_CROSS = "taker_at_cross"
    MAKER = "maker"
