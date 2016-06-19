#!/usr/bin/env python3.5
import transaction
from BTrees.IOBTree import IOBTree
from persistent.list import PersistentList

from challenge.models import OrderType


class MatchingEngine:
    def __init__(self, bids, asks, server):
        self.bids = bids  # type: IOBTree
        self.asks = asks  # type: IOBTree
        self.server = server  # type: ExchangeServer

    def insert_order(self, order, user, writer):
        storage = None
        if order.type == OrderType.bid:
            storage = self.bids
        elif order.type == OrderType.ask:
            storage = self.asks
        if order.price in storage.keys():
            storage[order.price].append(order)
        else:
            storage[order.price] = PersistentList([order])
        user.orders[order.id] = order
        transaction.commit()
        self.server.send_data({'type': 'orderCreated',
                               'id': order.id}, user=None, writer=writer)

    def delete_order(self, order):
        if order.type == OrderType.bid:
            storage = self.bids
        else:
            storage = self.asks
        order_list = storage[order.price]
        order_list.remove(order)
        if len(order_list) == 0:
            del storage[order.price]
        transaction.commit()

    def _send_report(self, amount, price, user=None, writer=None):
        data = {'type': 'trade',
                'price': price,
                'quantity': amount}
        self.server.send_data(data, user, writer)

    def _match_orders(self, order1, order2, writer1):
        assert order1.type != order2.type, "Orders must have different types to be matched"
        matched_amount = min(order1.quantity, order2.quantity)
        matched_price = order2.price
        matched_whole = False

        if matched_amount == order1.quantity:
            self.delete_order(order1)
            matched_whole = True
        else:
            order1.decrease_quantity(matched_amount)
        if matched_amount == order2.quantity:
            self.delete_order(order2)
        else:
            order2.decrease_quantity(matched_amount)
        transaction.commit()

        self._send_report(matched_amount, matched_price, None, writer1)
        self._send_report(matched_amount, matched_price, order2.user, None)

        return matched_whole

    def process_order(self, order, writer):
        matched = False
        while not matched:
            storage = None
            try:
                extreme_key = None
                if order.type == OrderType.bid:
                    storage = self.asks
                    extreme_key = self.asks.maxKey()
                    if extreme_key < order.price:
                        break
                elif order.type == OrderType.ask:
                    storage = self.bids
                    extreme_key = self.bids.minKey()
                    if extreme_key > order.price:
                        break
                matched_order = storage[extreme_key][0]
            except ValueError:
                break

            matched = self._match_orders(order, matched_order, writer)
