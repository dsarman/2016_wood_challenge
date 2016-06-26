.. wood_challenge documentation master file, created by
   sphinx-quickstart on Sun Jun 26 09:52:12 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. toctree::
   :maxdepth: 2

Documentation
*************
This package provides a simple server coded for the WOOD & Company Coding Challenge 2016.

For the server part, it uses pythons `asyncio <https://docs.python.org/3/library/asyncio.html>`_ library.

Orders are persisted using `ZODB <http://www.zodb.org/en/latest/>`_ object database.
Specifically using `BTree <https://pypi.python.org/pypi/BTrees>`_ for each side (BUY/ASK vs SELL/BID),
storing list of orders with the same price using it as key in the tree, which allows fast retrieval of relevant order
when trying to fill new order.

Test are written using the BDD testing framework `behave <http://pythonhosted.org/behave/>`_.


ExchangeServer
==============
.. autoclass:: challenge.server.ExchangeServer
    :members:
    :private-members:

MatchingEngine
==============
.. autoclass:: challenge.matching.MatchingEngine
    :members:
    :private-members: