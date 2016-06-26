#!/usr/bin/env python3.5
import logging
import transaction
from BTrees.OOBTree import OOBTree
from persistent.list import PersistentList
from challenge.models import OrderType
from datetime import datetime


class MatchingEngine:
    def __init__(self, bids, asks, server):
        self.bids = bids  # type: OOBTree
        self.asks = asks  # type: OOBTree
        self.server = server  # type: ExchangeServer
        self.log = logging.getLogger('MatchingEngine')  # type: logging.Logger

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
        self.log.info("New order created \"{}\"".format(order))
        self.server.send_data({'type': 'orderCreated',
                               'id': order.id}, user=None, writer=writer)

        data = self.get_price_sum_dict(storage[order.price])
        self.server.add_to_broadcast(data)

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
        self.log.info("Order \"{}\" was deleted.".format(order))

        if order.price in storage.keys():
            data = self.get_price_sum_dict(storage[order.price])
        else:
            side = self._get_opposite_side(order.type)
            data = self._make_price_sum_dict(side, order.price, 0)
        self.server.add_to_broadcast(data)

    @staticmethod
    def _make_price_sum_dict(order_side, price, quantity):
        return {'type': 'orderbook',
                'side': order_side,
                'price': price,
                'quantity': quantity}

    @staticmethod
    def _get_opposite_side(order_type):
        if order_type == OrderType.ask:
            return OrderType.bid.name
        else:
            return OrderType.ask.name

    @staticmethod
    def get_price_sum_dict(order_list):
        if not order_list:
            return None
        sum_quantity = 0
        price = order_list[0].price
        order_side = MatchingEngine._get_opposite_side(order_list[0].type)
        for order in order_list:
            sum_quantity += order.quantity
        return MatchingEngine._make_price_sum_dict(order_side,
                                                   price,
                                                   sum_quantity)

    @staticmethod
    def _get_exec_report_dict(amount, price):
        return {'type': 'trade',
                'time': datetime.now().timestamp(),
                'price': price,
                'quantity': amount}

    def _send_report(self, amount, price, user=None, writer=None):
        self.server.send_data(self._get_exec_report_dict(amount, price),
                              user, writer)

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
        self.log.info("Matched \"{}\" and \"{}\"".format(order1, order2))

        self._send_report(matched_amount, matched_price, None, writer1)
        self._send_report(matched_amount, matched_price, order2.user, None)

        if order1.type == OrderType.ask:
            order_list2 = self.bids.get(order2.price, None)
        else:
            order_list2 = self.asks.get(order2.price, None)

        data = self._get_exec_report_dict(matched_amount, matched_price)
        self.server.add_to_broadcast(data)
        data = self.get_price_sum_dict(order_list2)
        self.server.add_to_broadcast(data)

        return matched_whole

    def process_order(self, order, writer):
        def matching_loop(storage, extreme_key_func, compare_check_func):
            matched_whole = False
            while not matched_whole:
                try:
                    extreme_key = extreme_key_func()
                    if compare_check_func(extreme_key, order.price):
                        break
                    matched_order = storage[extreme_key][0]
                except ValueError:
                    break
                matched_whole = self._match_orders(order, matched_order, writer)
            return matched_whole

        self.log.debug("Starting matching of \"{}\"".format(order))
        if order.type == OrderType.bid:
            matched_storage = self.asks
            original_storage = self.bids
            extreme_key_func = self.asks.maxKey
            matched_whole = matching_loop(matched_storage, extreme_key_func, lambda x, y: x < y)
        else:
            matched_storage = self.bids
            original_storage = self.asks
            extreme_key_func = self.bids.minKey
            matched_whole = matching_loop(matched_storage, extreme_key_func, lambda x, y: x > y)

        if not matched_whole:
            data = self.get_price_sum_dict(original_storage[order.price])
            self.server.add_to_broadcast(data)

        self.log.debug("Stopped matching of \"{}\"".format(order))
