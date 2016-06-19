import transaction
from behave import *
from hamcrest import *


@given('"{username}" and "{password}"')
def step_impl(context, username, password):
    context.username = username
    context.password = password


@when("user connects")
def step_impl(context):
    context.connection_result = context.client.blocking_connect()


@step("sends login data")
def step_impl(context):
    context.client.send({'message': 'login',
                         'username': context.username,
                         'password': context.password})


@then("connection is successful")
def step_impl(context):
    assert_that(True, equal_to(context.connection_result))


@step("new user is created")
def step_impl(context):
    data = context.client.blocking_recv()
    assert_that({
        'type': 'login',
        'action': 'registered'
    }, equal_to(data))


@step("user is logged in")
def step_impl(context):
    data = context.client.blocking_recv()
    assert_that({
        'type': 'login',
        'action': 'logged_in'
    }, equal_to(data))


@then("login is denied")
def step_impl(context):
    data = context.client.blocking_recv()
    assert_that({
        'type': 'login',
        'action': 'denied'
    }, equal_to(data))


@step("sends bad login data")
def step_impl(context):
    context.client.send({'message': 'login',
                         'username': context.username,
                         'password': context.password + "BAAD"})


@step("disconnects")
def step_impl(context):
    context.client.disconnect()
