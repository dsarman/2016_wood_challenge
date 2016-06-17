import transaction
from behave import *
from hamcrest import *

# use_step_matcher("re")
from challenge.models import User


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
    assert_that(context.connection_result, equal_to(True))


@step("new user is created")
def step_impl(context):
    data = context.client.blocking_recv()
    assert_that(data, equal_to({
        'type': 'login',
        'action': 'registered'
    }))


@step("user is logged in")
def step_impl(context):
    data = context.client.blocking_recv()
    assert_that(data, equal_to({
        'type': 'login',
        'action': 'logged_in'
    }))


@then("login is denied")
def step_impl(context):
    data = context.client.blocking_recv()
    assert_that(data, equal_to({
        'type': 'login',
        'action': 'denied'
    }))

@step("sends bad login data")
def step_impl(context):
    context.client.send({'message': 'login',
                         'username': context.username,
                         'password': context.password + "BAAD"})


@step("disconnects")
def step_impl(context):
    context.client.disconnect()
