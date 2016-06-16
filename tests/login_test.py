#!/usr/bin/env python3.5

from hamcrest import *
from tests.helpers import ServerUnitTest

login_data = {'message': 'login',
              'username': 'test',
              'password': 'test'}


class LoginTest(ServerUnitTest):
    def test_register(self):
        self.client.blocking_connect()
        self.client.send(login_data)
        response = self.client.blocking_recv()
        assert_that(response, equal_to({'type': 'login',
                                        'action': 'registered'}))

    def test_login(self):
        self.client.blocking_connect()
        self.client.send(login_data)
        self.client.disconnect()
        self.client.blocking_connect()
        self.client.send(login_data)
        response = self.client.blocking_recv()
        assert_that(response, equal_to({'type': 'login',
                                        'action': 'logged_in'}))


class ConnectTest(ServerUnitTest):
    def test_connect(self):
        res = self.getResult(self.client.connect)
        assert_that(res, equal_to(True))
        self.client.disconnect()
