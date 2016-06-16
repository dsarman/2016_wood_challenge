#!/usr/bin/env python3.5

import ZODB
import asyncio
from hamcrest import *
from tests.helpers import ServerUnitTest

host = '127.0.0.1'
port = 15684
db = ZODB.DB(None)

login_data = {'message': 'login',
              'username': 'test',
              'password': 'test'}


class LoginTest(ServerUnitTest):
    def register_test(self):
        self.client.blocking_connect()
        self.client.send(login_data)
        response = self.client.blocking_recv()
        assert_that(response, equal_to({'type': 'login',
                                        'action': 'registered'}))

    def login_test(self):
        self.client.blocking_connect()
        self.client.send(login_data)
        response = self.client.blocking_recv()
        self.client.send(login_data)
        response = self.client.blocking_recv()
        assert_that(response, equal_to({'type': 'login',
                                        'action': 'loggedd_in'}))


class ConnectTest(ServerUnitTest):
    def test_connect(self):
        res = self.getResult(self.client.connect)
        assert_that(res, equal_to(True))
