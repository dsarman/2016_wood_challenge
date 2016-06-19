from behave import *
from hamcrest import *


@when("message with order data is received")
def step_impl(context):
    context.client.send({'message': 'createOrder',
                         'side': 'BUY',
                         'price': 100,
                         'quantity': 100})


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
