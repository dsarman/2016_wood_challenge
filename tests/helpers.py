import asyncio
import json
import threading
import unittest

import ZODB
import time

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

    def get_result(self, function):
        future = asyncio.Future(loop=self.loop)
        asyncio.ensure_future(function(future), loop=self.loop)
        self.loop.run_until_complete(future)
        return future.result()


class ServerUnitTest(unittest.TestCase):
    def setUp(self):
        self.server_loop = asyncio.new_event_loop()
        self.server = ExchangeServer(host, port, None, True)
        self.server_thread = threading.Thread(target=self.server.start, args=(ZODB.DB(None), self.server_loop))
        self.server_thread.start()

        time.sleep(0.01)

        self.client_loop = asyncio.new_event_loop()
        self.client = FakeClient(self.client_loop)

    def getResult(self, function):
        future = asyncio.Future(loop=self.client_loop)
        asyncio.ensure_future(function(future), loop=self.client_loop)
        self.client_loop.run_until_complete(future)
        return future.result()

    def tearDown(self):
        self.server_loop.call_soon_threadsafe(self.server.stop)
        self.server_thread.join()
        self.server_loop.close()
        self.client.disconnect()
        self.client_loop.close()
