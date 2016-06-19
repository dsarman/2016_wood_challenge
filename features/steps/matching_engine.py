import time
from behave import *
from decimal import Decimal
from hamcrest import *
from challenge.matching import MatchingEngine
from challenge.models import Order, OrderType


@given("orders data")
def step_impl(context):
    for row in context.table:
        context.matching_engine = MatchingEngine(context.bids, context.asks, context.fake_server)
        username = row['user']
        order_type = row['type'].upper()
        price = Decimal(row['price'])
        quantity = int(row['quantity'])
        order_id = int(time.time() * 10) - 14617000000
        order = Order()
        order.set_id(order_id)
        if order_type == 'BID':
            order.set_type(OrderType.bid)
        elif order_type == 'ASK':
            order.set_type(OrderType.ask)
        order.set_quantity(quantity)
        order.set_price(price)
        context.usernames[username] = order
        context.matching_engine.insert_order(order)
        context.matching_engine.process_order(order, None)


@then('limit order book has "{num}" orders')
def step_impl(context, num):
    bids_count = len(context.matching_engine.bids.keys())
    asks_count = len(context.matching_engine.asks.keys())
    assert_that(bids_count + asks_count, equal_to(int(num)), "Limit order book count")


@step('"{username}"\'s order quantity is "{quantity}"')
def step_impl(context, username, quantity):
    order = context.usernames[username]
    storage = None
    if order.type == OrderType.bid:
        storage = context.matching_engine.bids
    elif order.type == OrderType.ask:
        storage = context.matching_engine.asks
    for stored_order in storage[order.price]:
        if stored_order.id == order.id:
            assert_that(stored_order.quantity, equal_to(int(quantity)))
