from behave import *
from hamcrest import *


@when("message with order data is received")
def step_impl(context):
    context.client.send({'message': 'createOrder',
                         'side': 'BUY',
                         'price': 100,
                         'quantity': 100})
    context.price = 100
    context.quantity = 100


@then("order is created")
def step_impl(context):
    order = context.server.matching_engine.asks[context.price][0]
    assert_that(order, not_none())


@then("client receives the \"{num}\" created orders ids")
def step_impl(context, num):
    start_i = None
    for i in range(int(num)):
        reply = context.client.blocking_recv()
        if start_i is None:
            start_i = reply['id']
            expected_i = start_i
        else:
            expected_i = start_i + i
        assert_that(reply, equal_to({'type': 'orderCreated',
                                     'id': expected_i}))


@when("message to delete order is received")
def step_impl(context):
    context.client.send({'message': 'cancelOrder',
                         'orderId': context.order_id})


@step("order already exists")
def step_impl(context):
    context.execute_steps(u'''
        when message with order data is received
    ''')

    reply = context.client.blocking_recv()
    context.order_id = reply['id']


@then("order is deleted")
def step_impl(context):
    assert_that(len(context.server.matching_engine.asks.keys()), equal_to(0), "Limit order book size")