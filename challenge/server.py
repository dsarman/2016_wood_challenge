#!/usr/bin/env python3.5
from BTrees.OOBTree import OOBTree
from ZODB import FileStorage, DB
from challenge.models import User, Order, OrderType
import sys
import asyncio
import json
import transaction


def send_data(writer, data):
    msg = (json.dumps(data) + '\n').encode('utf-8')
    writer.write(msg)


async def recv_data(reader):
    msg = await reader.readline()
    msg = msg.decode('utf-8').rstrip('\n')
    return json.loads(msg)


class ExchangeServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.db = None
        self.connection = None
        self.db_root = None
        self.users = None
        self.bid_orders = None
        self.ask_orders = None
        self.server = None
        self.loop = None
        self.logged_in_clients = {}
        self.order_queue = asyncio.Queue(loop=self.loop)

    async def _accept_connection(self, reader, writer):
        login_data = await recv_data(reader)
        user, login_response = self._login(login_data)
        send_data(writer, login_response)
        if user is None:
            writer.close()
        else:
            # start new Task to handle this specific client connection
            task = asyncio.Task(self._handle_client(reader, writer, user))
            self.logged_in_clients[task] = (reader, writer)

            def client_done(done_task):
                print("Client task done:{}".format(done_task))
                del self.logged_in_clients[done_task]

            task.add_done_callback(client_done)

    async def _handle_client(self, reader, writer, user):
        while True:
            data = await recv_data(reader)
            if not data:  # empty string means the client disconnected
                break
            msg_type = data['message']
            if msg_type == 'createOrder':
                self._create_order(writer, data, user)
            elif msg_type == 'cancelOrder':
                raise NotImplementedError
            else:
                raise ValueError("Message has to have a valid \'message\' field.")

            await writer.drain()

    def _create_order(self, writer, order_data, user):
        new_order = Order()
        new_order.set_user(user)
        new_order.set_price(order_data['price'])
        new_order.set_quantity(order_data['quantity'])
        new_order.set_id(order_data['order_id'])
        if order_data['side'] == 'BUY':
            new_order.set_type(OrderType.ask)
        elif order_data['side'] == 'SELL':
            new_order.set_type(OrderType.bid)
        else:
            raise ValueError("Create order needs to have type \'BUY\' or \'SELL\'")
        transaction.commit()



        self.order_queue.put((new_order, writer))

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
            return None, data
        else:
            data['action'] = 'denied'
            return None, data

    def init_db(self, db: DB):
        self.db = db
        self.connection = db.open()
        self.db_root = self.connection.root()
        if 'userdb' not in self.db_root.keys():
            self.db_root['userdb'] = OOBTree()
        self.users = self.db_root['userdb']

        if 'biddb' not in self.db_root.keys():
            self.bid_orders = self.db_root['biddb']

        if 'askdb' not in self.db_root.keys():
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
        handle_coro = asyncio.start_server(self._accept_connection, self.host, self.port, loop=self.loop)
        self.server = self.loop.run_until_complete(handle_coro)

        print("Serving on {}".format(self.server.sockets[0].getsockname()))

        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            pass

    def stop(self):
        if self.server is not None:
            self.server.close()
            self.loop.run_until_complete(self.server.wait_closed())
            self.server = None
            self.loop.close()


if __name__ == '__main__':
    assert len(sys.argv) >= 3, 'Usage: server.py host port'
    host = sys.argv[1]
    port = int(sys.argv[2])
    db = None
    if len(sys.argv) >= 4 and sys.argv[3] == '--memory-db':
        db = DB(None)

    server = ExchangeServer(host, port)
    server.start(db)
