#!/usr/bin/env python3.5
import asyncio
from uuid import UUID
from persistent import Persistent
from bcrypt import hashpw, gensalt
from enum import Enum
from decimal import Decimal
from persistent.dict import PersistentDict


def get_passw_hash(password, salt=gensalt()):
    return hashpw(password.encode('utf-8'), salt)


class User(Persistent):
    def __init__(self) -> None:
        self.username = None  # type: str
        self.password = None  # type: bytes
        self.writer = None  # type: asyncio.StreamWriter
        self.orders = PersistentDict()  # type: PersistentDict[int, Order]

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
        self.type = None  # type: OrderType
        self.user = None  # type: User
        self.price = None  # type: Decimal
        self.quantity = None  # type: int
        self.id = None  # type: UUID

    def set_type(self, order_type: OrderType):
        self.type = order_type

    def set_user(self, user: User):
        self.user = user

    def set_price(self, price: Decimal):
        self.price = price

    def set_quantity(self, quantity: int):
        self.quantity = quantity

    def decrease_quantity(self, quantity: int):
        assert self.quantity >= quantity, "Cannot decrease into negative"
        self.quantity -= quantity

    def set_id(self, id: int):
        self.id = id
