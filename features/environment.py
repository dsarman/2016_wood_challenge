import asyncio
import json
import threading

import time

import ZODB

from challenge.server import ExchangeServer

host = '127.0.0.1'
port = 1234


class FakeClient:
    def __init__(self, loop):
        self.loop = loop
        self.reader = None
        self.writer = None

    async def connect(self, future):
        reader, writer = await asyncio.open_connection(host, port, loop=self.loop)
        self.reader = reader
        self.writer = writer
        if reader is not None and writer is not None:
            future.set_result(True)
        else:
            future.set_result(False)

    def blocking_connect(self):
        return self.get_result(self.connect)

    def disconnect(self):
        if self.writer is not None:
            self.writer.close()

    def send(self, data):
        msg = (json.dumps(data) + '\n').encode('utf-8')
        self.writer.write(msg)

    async def recv(self, future):
        msg = await self.reader.readline()
        msg = msg.decode('utf-8').rstrip('\n')
        data = json.loads(msg)
        future.set_result(data)

    def blocking_recv(self):
        return self.get_result(self.recv)

    def is_disconnected(self):
        return self.reader.at_eof()

    def get_result(self, function):
        future = asyncio.Future(loop=self.loop)
        asyncio.ensure_future(function(future), loop=self.loop)
        self.loop.run_until_complete(future)
        return future.result()


def before_scenario(context, scenario):
    context.server_loop = asyncio.new_event_loop()
    context.db = ZODB.DB(None)
    context.server = ExchangeServer(host, port, None, True)
    context.server_thread = threading.Thread(
        target=context.server.start,
        args=(context.db, context.server_loop))
    context.server_thread.start()

    time.sleep(1)

    context.client_loop = asyncio.new_event_loop()
    context.client = FakeClient(context.client_loop)

    # context.db_connection = context.db.open()
    # context.db_root = context.db_connection.root()


def after_scenario(context, scenario):
    context.server_loop.call_soon_threadsafe(context.server.stop)
    context.server_thread.join()
    context.server_loop.close()
    context.client.disconnect()
    context.client_loop.close()
