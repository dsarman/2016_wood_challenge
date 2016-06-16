#!/usr/bin/env python3.5

from persistent import Persistent
from bcrypt import hashpw, gensalt
from enum import Enum
from decimal import Decimal


def get_passw_hash(password, salt=gensalt()):
    return hashpw(password.encode('utf-8'), salt)


class User(Persistent):
    def __init__(self) -> None:
        self.username = None  # type: str
        self.password = None  # type: bytes

    def set_username(self, username: str) -> None:
        self.username = username

    def set_password(self, password: str) -> None:
        self.password = get_passw_hash(password)

    def check_password(self, password: str) -> bool:
        return get_passw_hash(password, self.password) == self.password


class OrderType(Enum):
    bid = 1
    ask = 2


class Order(Persistent):
    def __init__(self) -> None:
        self.order_type = None  # type: OrderType
        self.user = None  # type: User
        self.price = None  # type: Decimal
        self.quantity = None  # type: int

    def set_type(self, order_type: OrderType):
        self.order_type = order_type

    def set_user(self, user: User):
        self.user = user

    def set_price(self, price: Decimal):
        self.price = price

    def set_quantity(self, quantity: int):
        self.quantity = quantity


class Trade(Persistent):
    def __init__(self) -> None:
        self.bid_order = None  # type: Order
        self.ask_order = None  # type: Order

    def set_bid_order(self, order: Order):
        assert order.type == OrderType.bid, "Order needs to be of bid type"
        self.bid_order = order

    def set_ask_order(self, order: Order):
        assert order.type == OrderType.ask, "Order needs to be of ask type"
        self.ask_order = order
