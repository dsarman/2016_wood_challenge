#!/usr/bin/env python3.5

from ZODB import FileStorage, DB
import asyncio
import sys
import json


class ExchangeServer:
    """
    TCP Server heavily based on asyncio example
    https://github.com/python/asyncio/blob/master/examples/simple_tcp_server.py
    """

    def __init__(self):
        self.server = None
        self.clients = {}
        self.db = None
        self.connection = None
        self.db_root = None

    def _accept_client(self, client_reader, client_writer) -> None:
        """
        Accepts a new client connection and creates a Task to handle this client.
        self.clients is updated to keep track of new client.
        """
        task = asyncio.Task(self._handle_client(client_reader, client_writer))
        self.clients[task] = (client_reader, client_writer)

        def client_done(done_task):
            print("Client task done:", done_task, file=sys.stderr)
            del self.clients[done_task]

        task.add_done_callback(client_done)

    async def _handle_client(self, client_reader, client_writer):
        """
        Does the work to handle request for specific client.
        """
        while True:
            data = (await client_reader.readline()).decode("utf-8").rstrip('\n')
            if not data:  # empty string means the client disconnected
                break
            data_dict = json.loads(data)
            message_type = data_dict['message']
            if message_type == 'createOrder':
                raise NotImplementedError
            elif message_type == 'cancelOrder':
                raise NotImplementedError
            elif message_type == 'register':
                raise NotImplementedError
            else:
                raise ValueError('Unexpected client message type: {}'.format(message_type))

            await client_writer.drain()

    def start_tcp(self, loop: asyncio.AbstractEventLoop, host: str, port: int) -> None:
        """
        Starts the TCP server, and listens on specified host and port

        For each client that connects, the accept_client method gets called.
        This method runs the loop until the server sockets are ready to accept connections.
        """
        self.server = loop.run_until_complete(
            asyncio.streams.start_server(self._accept_client,
                                         host, port,
                                         loop=loop))

    def start(self, db: DB, host: str, port: int, loop: asyncio.AbstractEventLoop=None):
        self.connect_db(db)
        if loop is None:
            self.start_tcp(asyncio.get_event_loop(), host, port)
        else:
            self.start_tcp(loop, host, port)

    def connect_db(self, db: DB):
        self.db = db
        self.connection = db.open()
        self.db_root = self.connection.root()

    def stop(self, loop: asyncio.AbstractEventLoop) -> None:
        """
        Stops the TCP server, i.e. closes the listening socket(s)

        This method runs the loop until the server sockets are closed.
        """
        if self.server is not None:
            self.server.close()
            loop.run_until_complete(self.server.wait_closed())
            self.server = None

if __name__ == '__main__':
    assert len(sys.argv) == 3, 'Usage: server.py hostname port'
    host = sys.argv[1]
    port = int(sys.argv[2])

    storage = FileStorage.FileStorage('database.fs')
    db = DB(storage)

    loop = asyncio.get_event_loop()

    server = ExchangeServer()
    server.connect_db(db)
    server.start_tcp(loop, host, port)
