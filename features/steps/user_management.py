#!/usr/bin/env python3.5

import asyncio
from behave import *
from challenge.server import ExchangeServer
import threading
import ZODB
import json

global host, port, db, loop
host = '127.0.0.1'
port = 15684
db = ZODB.DB(None)
loop = asyncio.get_event_loop()


def start_server():
    server = ExchangeServer()
    server_thread = threading.Thread(target=server.start(db, host, port))
    server_thread.start()
    return server_thread


async def client(send_data, result):
    reader, writer = await asyncio.streams.open_connection(
        host, port, loop=loop)

    def send(data):
        msg = (json.dumps(data) + '\n').encode('utf-8')
        writer.write(msg)

    async def recv():
        msg = (await reader.readline()).decode('utf-8').rstrip()
        return json.loads(msg)

    send(send_data)
    writer.close()
    result = await recv()


@given("username and password")
def step_impl(context):
    start_server()
    context.username = context.table[0]['username']
    context.password = context.table[0]['password']


@when(u'registering')
def step_impl(context):
    data = {'message': 'register',
            'username': context.username,
            'password': context.password}
    result = None
    loop.run_until_complete(client(data, result))
    context.result = result


@then(u'new user is created')
def step_impl(context):
    assert context.result, "Register response must not be empty"
    print(context.result)


@given(u'username and password of existing user')
def step_impl(context):
    raise NotImplementedError(u'STEP: Given username and password of existing user')


@then(u'new user is not created')
def step_impl(context):
    raise NotImplementedError(u'STEP: Then new user is not created')
