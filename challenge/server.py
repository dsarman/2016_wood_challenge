#!/usr/bin/env python3.5
import uuid
from logging import Logger
from typing import List
from challenge.matching import MatchingEngine
from challenge.models import User, Order, OrderType
from typing import Dict, Any
from asyncio import StreamReader, StreamWriter, AbstractEventLoop, AbstractServer, new_event_loop, start_server, Queue
import logging
import ZODB
import ZODB.Connection
import ZODB.FileStorage
import persistent
import persistent.mapping
import decimal
import BTrees.OOBTree
import sys
import json
import transaction


class ExchangeServer:
    """
    Simple asyncio TCP server for one stock.
    """

    def __init__(self, host, private_port, public_port=None, debug=False):
        self.host = host  # type: str
        self.private_port = private_port  # type: int
        self.public_port = public_port  # type: int
        self.debug = debug  # type: bool
        self.db = None  # type: ZODB.DB
        self.connection = None  # type: ZODB.Connection.Connection
        self.db_root = None  # type: persistent.mapping.PersistentMapping
        self.users = None  # type:  BTrees.OOBTree.OOBTree
        self.bid_orders = None  # type: BTrees.OOBTree.OOBTree
        self.ask_orders = None  # type: BTrees.OOBTree.OOBTree
        self.private_server = None  # type: AbstractServer
        self.public_server = None  # type: AbstractServer
        self.loop = None  # type: AbstractEventLoop
        self.private_clients = {}  # type: Dict[str, (StreamReader, StreamWriter)]
        self.public_clients = []  # type: List[StreamWriter]
        self.matching_engine = None  # type: MatchingEngine
        self.broadcast_queue = None  # type: Queue
        self.id_counter = 0  # type: int
        self.log = logging.getLogger('ExchangeServer')  # type: Logger
        if debug:
            self.log.setLevel(logging.DEBUG)

    async def _accept_private_connection(self, reader: StreamReader, writer: StreamWriter) -> None:
        """
        Coroutine that accepts incoming client connections, launches the login process
        and message handling coroutine.

        :param reader: Connected clients Reader.
        :param writer: Connected clients Writer.
        """
        msg = await reader.readline()
        login_data = self._decode_msg(msg)
        user, login_response = self._login(login_data)
        self._send_data(writer, login_response)
        if user is None:
            writer.close()
            self.log.debug("Client connection has been denied")
        else:
            self.private_clients[user.username] = (reader, writer)
            self.log.info("Client connected as \"{}\"".format(user.username))
            await self._handle_client(reader, writer, user)

    async def _accept_public_connection(self, _, writer: StreamWriter) -> None:
        """
        Accepts incoming connection from public client and ads it to notification list.

        :param _: Clients Reader. Not needed since public clients only consume data.
        :param writer: Clients Writer.
        """
        self.public_clients.append(writer)
        await self._broadcast_orderbook(writer)

    def add_to_broadcast(self, data: Dict[str, Any]) -> None:
        """
        Adds data to Queue for public broadcasting.

        :param data: Data to be broadcasted.
        """
        if data is not None:
            self.broadcast_queue.put(data)

    async def _broadcast_orderbook(self, writer: StreamWriter) -> None:
        """
        Coroutine that sends orderbook data to writer, each price and its quantity as separate message.

        :param writer: Writer used for sending data.
        """
        for storage in (self.bid_orders, self.ask_orders):
            for order_list in storage.values():
                data = self.matching_engine.get_price_sum_dict(order_list)
                self._send_data(writer, data)

    async def _broadcast_public(self) -> None:
        """
        Coroutine which takes data to be broadcasted from queue, and sends it to all
        connected public clients.
        """
        while True:
            data = await self.broadcast_queue.get()
            for writer in self.public_clients:
                self._send_data(writer, data)
                await writer.drain()

    async def _handle_client(self, reader: StreamReader, writer: StreamWriter, user: User) -> None:
        """
        Coroutine which loops over the received lines and launches corresponding action.
        Does the main work with handling private client messages.

        :param reader: Clients reader.
        :param writer: Clients writer.
        :param user: User under which the client is logged in.
        """
        while True:
            msg = await reader.readline()
            if not msg:  # empty string means the client disconnected
                break
            data = self._decode_msg(msg)
            msg_type = data['message']
            if msg_type == 'createOrder':
                self._create_order(writer, data, user)
            elif msg_type == 'cancelOrder':
                self._delete_order(data, user)
            else:
                raise ValueError("Message has to have a valid \'message\' field.")

            await writer.drain()
        del self.private_clients[user.username]

    def _delete_order(self, order_data: Dict[str, Any], user: User) -> None:
        """
        Deletes order with given order id.

        :param order_data: Dictionary containing order id data.
        :param user: User whose order we want to delete.
        """
        order_id = order_data['orderId']
        order = user.orders[order_id]
        self.matching_engine.delete_order(order)

    def _create_order(self, writer: StreamWriter, order_data: Dict[str, Any], user: User) -> None:
        """
        Create new order from user using order data.
        Writer is passed along to allow reporting status to user without looking up his writer.

        :param writer: Writer of the client who created the order.
        :param order_data: Dictionary with orders data.
        :param user: User who created the order.
        """
        new_order = Order()
        new_order.set_user(user)
        new_order.set_price(decimal.Decimal(order_data['price']))
        new_order.set_quantity(int(order_data['quantity']))
        new_order.set_id(uuid.uuid4())
        if order_data['side'] == 'BUY':
            new_order.set_type(OrderType.ask)
        elif order_data['side'] == 'SELL':
            new_order.set_type(OrderType.bid)
        else:
            raise ValueError("Create order needs to have type \'BUY\' or \'SELL\'")

        self.matching_engine.insert_order(new_order, user, writer)
        self.matching_engine.process_order(new_order, writer)

    def _login(self, login_data: Dict[str, Any]) -> (User, Dict[str, Any]):
        """
        Tries to log in given supplied login data.

        :param login_data: Data containing user login info.
        :return: Tipple containing corresponding user, and response to be sent to user if the loggin was successful.
            If the loggin was not successful, first return value is None, second message to user.
        """
        data = {'type': 'login'}
        if 'message' not in login_data or login_data['message'] != 'login':
            data['action'] = 'denied'
            return False, data
        username = login_data['username']
        password = login_data['password']
        password_matches = None
        if username in self.users.keys():
            user = self.users[username]
            password_matches = user.check_password(password)
        else:
            user = User()
            user.set_username(username)
            user.set_password(password)
            self.users[username] = user
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
    def _send_data(writer: StreamWriter, data: Dict[str, Any]) -> None:
        """
        Sends data using supplied writer.

        :param writer: Writer used for sending data.
        :param data: Dictionary of data to be sent.
        """
        def decimal_decode(obj):
            if isinstance(obj, decimal.Decimal):
                return str(obj)

        msg = (json.dumps(data, default=decimal_decode) + '\n').encode('utf-8')
        writer.write(msg)

    @staticmethod
    def _decode_msg(msg: bytes) -> Dict[str, Any]:
        """
        Decodes message from json string to python dictionary.

        :param msg: Raw message to be decoded.
        :return: Dictionary representing parsed json.
        """
        assert msg is not None, "Cannot decode empty message"
        msg = msg.decode('utf-8').rstrip('\n')
        return json.loads(msg)

    def send_data(self, data: Dict[str, str], user: User = None, writer: StreamWriter = None) -> None:
        """
        Sends data using supplied writer.
        If no writer is supplied, retrieve it for the supplied user.

        :param data: Data to be sent
        :param user: User which is recipient of the data.
        :param writer: Writer used to send the data.
        """
        assert user is not None or writer is not None, "You must supply user or writer"
        if writer is not None or user.username in self.private_clients.keys():
            if writer is None:
                writer = self.private_clients[user.username][1]
            self._send_data(writer, data)

    def get_new_id(self):
        """
        Simple function used to generate new ids for orders

        :return: New Id.
        """
        self.id_counter += 1
        return self.id_counter

    def init_db(self, db: ZODB.DB) -> None:
        """
        Opens database connection and eventually creates nonexistent indexes.

        :param db: DB to be opened.
        """
        self.db = db
        self.connection = db.open()
        self.db_root = self.connection.root()
        if 'userdb' not in self.db_root.keys():
            self.db_root['userdb'] = BTrees.OOBTree.OOBTree()
        self.users = self.db_root['userdb']

        if 'biddb' not in self.db_root.keys():
            self.db_root['biddb'] = BTrees.OOBTree.OOBTree()
        self.bid_orders = self.db_root['biddb']

        if 'askdb' not in self.db_root.keys():
            self.db_root['askdb'] = BTrees.OOBTree.OOBTree()
        self.ask_orders = self.db_root['askdb']

        if 'maxcounter' not in self.db_root.keys():
            self.db_root['maxcounter'] = 0
        self.id_counter = self.db_root['maxcounter']

    def start(self, db: ZODB.DB = None, loop: AbstractEventLoop = None) -> None:
        """
        Starts the exchange server.
        If database and/or loop is not supplied, create default ones.

        :param db: DB used in the server.
        :param loop: asyncio loop used in the server.
        """
        if loop is None:
            self.loop = new_event_loop()
        else:
            self.loop = loop
        self.broadcast_queue = Queue(loop=self.loop)

        if db is None:
            storage = ZODB.FileStorage.FileStorage('database.fs')
            db = ZODB.DB(storage)
        self.init_db(db)
        self.matching_engine = MatchingEngine(self.bid_orders, self.ask_orders, self)

        if self.private_port is not None:
            private_handle_coro = start_server(self._accept_private_connection, self.host, self.private_port,
                                               loop=self.loop, reuse_address=True)
            self.private_server = self.loop.run_until_complete(private_handle_coro)
            print("Serving private on {}".format(self.private_server.sockets[0].getsockname()))
        if self.public_port is not None:
            public_handle_coro = start_server(self._accept_public_connection, self.host, self.public_port,
                                              loop=self.loop, reuse_address=True)
            self.public_server = self.loop.run_until_complete(public_handle_coro)
            print("Serving public on {}".format(self.public_server.sockets[0].getsockname()))

        try:
            self.loop.run_until_complete(self._broadcast_public())
        except KeyboardInterrupt:
            pass

    def stop(self) -> None:
        """
        Stops the running server (both public and private).
        *NOTE*: Currently does not function correctly, constantly throws RuntimeError.
        """
        for server in (self.private_server, self.public_server):
            if server is not None:
                try:
                    server.close()
                    self.loop.run_until_complete(server.wait_closed())
                # TODO fix server not shutting down without exception in tests
                except RuntimeError:
                    pass
        self.loop.close()


if __name__ == '__main__':
    assert len(sys.argv) >= 4, 'Usage: server.py host private-port public-port'
    host = sys.argv[1]
    private_port = int(sys.argv[2])
    public_port = int(sys.argv[3])
    db = None
    debug = False
    if len(sys.argv) >= 5 and sys.argv[4] == '--memory-db':
        db = ZODB.DB(None)
    if len(sys.argv) >= 6 and sys.argv[5] == '--debug':
        debug = True

    server = ExchangeServer(host, private_port, public_port, debug)
    server.start(db)
