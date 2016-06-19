import asyncio
from behave import *
from environment import FakeClient

loop = asyncio.new_event_loop()

def create_client():
    # loop = asyncio.new_event_loop()
    client = FakeClient(loop)
    return client, loop


@given("logged in user {username}")
def step_impl(context, username):
    client, loop = create_client()
    context.clients[username] = (client, loop)
    client.blocking_connect()
    client.send({'message': 'login',
                 'username': username,
                 'password': 'pass'})
    client.blocking_recv()


@given("client is instantiated")
def step_impl(context):
    client, loop = create_client()
    context.client = client
    context.client_loop = loop
