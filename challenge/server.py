#!/usr/bin/env python3.5
from BTrees.OOBTree import OOBTree
from ZODB import FileStorage, DB
from decimal import Decimal

from challenge.matching import MatchingEngine
from challenge.models import User, Order, OrderType
import sys
import asyncio
import json
import transaction


def decimal_decode(obj):
    if isinstance(obj, Decimal):
        return str(obj)


class ExchangeServer:
    def __init__(self, host, port, debug=False):
        self.host = host
        self.port = port
        self.debug = debug
        self.db = None
        self.connection = None
        self.db_root = None
        self.users = None
        self.bid_orders = None
        self.ask_orders = None
        self.server = None
        self.loop = None
        self.logged_in_clients = {}
        self.matching_engine = None

    async def _accept_connection(self, reader, writer):
        msg = await reader.readline()
        login_data = self._decode_msg(msg)
        user, login_response = self._login(login_data)
        self._send_data(writer, login_response)
        print("After send user is {}".format(user))
        if user is None:
            writer.close()
        else:
            self.logged_in_clients[user.username] = (reader, writer)
            print("Logged in clients: {}".format(self.logged_in_clients))
            await self._handle_client(reader, writer, user)

    async def _handle_client(self, reader, writer, user):
        while True:
            msg = await reader.readline()
            if not msg:  # empty string means the client disconnected
                break
            data = self._decode_msg(msg)
            msg_type = data['message']
            if msg_type == 'createOrder':
                self._create_order(writer, data, user)
            elif msg_type == 'cancelOrder':
                raise NotImplementedError
            else:
                raise ValueError("Message has to have a valid \'message\' field.")

            await writer.drain()
        del self.logged_in_clients[user.username]

    def _create_order(self, writer, order_data, user):
        print("Creating order")
        new_order = Order()
        new_order.set_user(user)
        new_order.set_price(int(order_data['price']))
        new_order.set_quantity(int(order_data['quantity']))
        new_order.set_id(int(order_data['orderId']))
        if order_data['side'] == 'BUY':
            new_order.set_type(OrderType.ask)
        elif order_data['side'] == 'SELL':
            new_order.set_type(OrderType.bid)
        else:
            raise ValueError("Create order needs to have type \'BUY\' or \'SELL\'")

        self.matching_engine.insert_order(new_order)
        self.matching_engine.process_order(new_order, writer)

    def _login(self, login_data):
        data = {'type': 'login'}
        if 'message' not in login_data or login_data['message'] != 'login':
            data['action'] = 'denied'
            return False, data
        username = login_data['username']
        password = login_data['password']
        password_matches = None
        user = None
        if username in self.users.keys():
            user = self.users[username]
            password_matches = user.check_password(password)
        else:
            user = User()
            user.set_username(username)
            user.set_password(password)
            self.users[username] = user
            print("Creating new user: {}".format(user))
            transaction.commit()
        if password_matches:
            data['action'] = 'logged_in'
            return user, data
        elif password_matches is None:
            data['action'] = 'registered'
            return user, data
        else:
            data['action'] = 'denied'
            return None, data

    @staticmethod
    def _send_data(writer, data):
        msg = (json.dumps(data, default=decimal_decode) + '\n').encode('utf-8')
        writer.write(msg)

    def _decode_msg(self, msg):
        assert msg is not None, "Cannot decode empty message"
        msg = msg.decode('utf-8').rstrip('\n')
        return json.loads(msg)

    def send_data(self, data, user=None, writer=None):
        assert user is not None or writer is not None, "You must supply user or writer"
        if writer is not None or user.username in self.logged_in_clients.keys():
            if writer is None:
                writer = self.logged_in_clients[user.username][1]
            self._send_data(writer, data)

    def init_db(self, db: DB):
        self.db = db
        self.connection = db.open()
        self.db_root = self.connection.root()
        if 'userdb' not in self.db_root.keys():
            self.db_root['userdb'] = OOBTree()
        self.users = self.db_root['userdb']

        if 'biddb' not in self.db_root.keys():
            self.db_root['biddb'] = OOBTree()
        self.bid_orders = self.db_root['biddb']

        if 'askdb' not in self.db_root.keys():
            self.db_root['askdb'] = OOBTree()
        self.ask_orders = self.db_root['askdb']

    def start(self, db=None, loop=None):
        if loop is None:
            self.loop = asyncio.new_event_loop()
        else:
            self.loop = loop
        if db is None:
            storage = FileStorage.FileStorage('database.fs')
            db = DB(storage)
        self.init_db(db)
        self.matching_engine = MatchingEngine(self.bid_orders, self.ask_orders, self)

        handle_coro = asyncio.start_server(self._accept_connection, self.host, self.port, loop=self.loop)
        self.server = self.loop.run_until_complete(handle_coro)

        print("Serving on {}".format(self.server.sockets[0].getsockname()))

        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            pass

    def stop(self):
        # TODO find a nicer solution
        try:
            if self.server is not None:
                self.server.close()
                self.loop.run_until_complete(self.server.wait_closed())
                self.server = None
                self.loop.close()
        except RuntimeError as e:
            if str(e) != "Event loop is running.":
                raise e


if __name__ == '__main__':
    assert len(sys.argv) >= 3, 'Usage: server.py host port'
    host = sys.argv[1]
    port = int(sys.argv[2])
    db = None
    if len(sys.argv) >= 4 and sys.argv[3] == '--memory-db':
        db = DB(None)

    server = ExchangeServer(host, port)
    server.start(db)
