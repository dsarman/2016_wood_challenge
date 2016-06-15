#!/usr/bin/env python3.5

from behave import *
from challenge.server import ExchangeServer
import threading
import ZODB
import socket
import json

global host, port, db
host = '127.0.0.1'
port = 15684
db = ZODB.DB(None)


def start_server():
    server = ExchangeServer()
    server_thread = threading.Thread(target=server.start(db, host, port))
    server_thread.start()
    return server_thread


@given("username and password")
def step_impl(context):
    context.st = start_server()
    context.client_socket = socket.socket()
    context.client_socket.connect((host, port))
    context.username = context.table[0]['username']
    context.password = context.table[0]['password']


@when(u'registering')
def step_impl(context):
    s = context.client_socket

    data = {'message': 'register',
            'username': context.username,
            'password': context.password}
    json_data = json.dumps(data)
    sent = s.send(json_data.encode('utf-8') + b'\n')
    assert sent != 0, "Register was unsuccessful, no data was sent."


@then(u'new user is created')
def step_impl(context):
    connection = db.open()
    root = connection.root()
    print(root.users)
    assert root.users, "User db should not be empty"


@given(u'username and password of existing user')
def step_impl(context):
    raise NotImplementedError(u'STEP: Given username and password of existing user')


@then(u'new user is not created')
def step_impl(context):
    raise NotImplementedError(u'STEP: Then new user is not created')
