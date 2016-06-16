#!/usr/bin/env python3.5
import sys
from BTrees.OOBTree import OOBTree
from ZODB import FileStorage, DB
import asyncio
import json
import transaction

from challenge.models import User


def send_data(writer, data):
    msg = (json.dumps(data) + '\n').encode('utf-8')
    writer.write(msg)


async def recv_data(reader):
    msg = await reader.readline()
    msg = msg.decode('utf-8').rstrip('\n')
    return json.loads(msg)


class ExchangeServer:
    def __init__(self):
        self.db = None
        self.connection = None
        self.db_root = None
        self.users = None
        self.server = None
        self.loop = None
        self.logged_in_clients = {}

    async def _accept_connection(self, reader, writer):
        login_data = await recv_data(reader)
        logged_in, login_response = self._login(login_data)
        send_data(writer, login_response)
        if not logged_in:
            writer.close()
        else:
            # start new Task to handle this specific client connection
            task = asyncio.Task(self._handle_client(reader, writer))
            self.logged_in_clients[task] = (reader, writer)

            def client_done(done_task):
                print("Client task done:{}".format(done_task))
                del self.logged_in_clients[done_task]

            task.add_done_callback(client_done)

    async def _handle_client(self, reader, writer):
        while True:
            data = await recv_data(reader)
            if not data:  # empty string means the client disconnected
                break
            msg_type = data['message']
            if msg_type == 'createOrder':
                raise NotImplementedError
            elif msg_type == 'cancelOrder':
                raise NotImplementedError
            else:
                raise ValueError("Message has to have a valid \'message\' field.")

            await writer.drain()

    def _login(self, login_data):
        data = {'type': 'login'}
        if 'message' not in login_data or login_data['message'] != 'login':
            data['action'] = 'denied'
            return False, data
        username = login_data['username']
        password = login_data['password']
        password_matches = None
        if username in self.users.keys():
            password_matches = self.users[username].check_password(password)
        else:
            user = User()
            user.set_username(username)
            user.set_password(password)
            self.users[username] = user
            print("Creating new user: {}".format(user))
            transaction.commit()

        if password_matches:
            data['action'] = 'logged_in'
            return True, data
        elif password_matches is None:
            data['action'] = 'registered'
            return False, data
        else:
            data['action'] = 'denied'
            return False, data

    def init_db(self, db: DB):
        self.db = db
        self.connection = db.open()
        self.db_root = self.connection.root()
        if 'userdb' not in self.db_root.keys():
            self.db_root['userdb'] = OOBTree()
        self.users = self.db_root['userdb']

    def start(self, host, port, db=None, loop=None):
        if loop is None:
            self.loop = asyncio.get_event_loop()
        else:
            self.loop = loop
        if db is None:
            storage = FileStorage.FileStorage('database.fs')
            db = DB(storage)
        self.init_db(db)
        handle_coro = asyncio.start_server(self._accept_connection, host, port, loop=self.loop)
        self.server = self.loop.run_until_complete(handle_coro)

        print("Serving on {}".format(self.server.sockets[0].getsockname()))

        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            pass

    def stop(self):
        self.server.close()
        self.loop.run_until_complete(self.server.wait_closed())
        self.loop.close()

if __name__ == '__main__':
    assert len(sys.argv) >= 3, 'Usage: server.py host port'
    host = sys.argv[1]
    port = int(sys.argv[2])
    db = None
    if len(sys.argv) >= 4 and sys.argv[3] == '--memory-db':
        db = DB(None)

    server = ExchangeServer()
    server.start(host, port, db)
