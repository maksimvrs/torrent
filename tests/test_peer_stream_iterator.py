import asyncio
import unittest

from src.peer_streem_iterator import PeerStreamIterator
from src.peer_protocol import *


class Reader:
    def __init__(self, data):
        self._data = data

    async def read(self, size):
        try:
            return self._data.pop(0)
        except IndexError:
            return b''


class PeerTests(unittest.TestCase):
    def async_test(f):
        def wrapper(*args, **kwargs):
            coro = asyncio.coroutine(f)
            future = coro(*args, **kwargs)
            loop = asyncio.get_event_loop()
            loop.run_until_complete(future)

        return wrapper

    @async_test
    async def test_bitfield(self):
        reader = Reader([b'\x00\x00\x00\xd2\x05'
                         b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                         b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                         b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                         b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                         b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                         b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                         b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                         b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                         b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                         b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                         b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                         b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                         b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                         b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                         b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                         b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                         b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                         b'\xff\xff\xff\xff\xf0'])
        buffer = b''
        result = None
        async for message in PeerStreamIterator(reader, buffer):
            result = message
            if result is not None:
                break
        self.assertIsInstance(result, BitField)

    @async_test
    async def test_unchoke(self):
        reader = Reader([b'\x00\x00\x00\x01\x01'])
        buffer = b''
        result = None
        async for message in PeerStreamIterator(reader, buffer):
            result = message
            if result is not None:
                break
        self.assertIsInstance(result, Unchoke)

    @async_test
    async def test_piece(self):
        with open('./data/piece', 'rb') as file:
            data = file.read()

        reader = Reader([data])

        buffer = b''
        result = None
        async for message in PeerStreamIterator(reader, buffer):
            result = message
            if result is not None:
                break
        self.assertIsInstance(result, Piece)

    @async_test
    async def test_choke(self):
        reader = Reader([b'\x00\x00\x00\x01\x00'])
        buffer = b''
        result = None
        async for message in PeerStreamIterator(reader, buffer):
            result = message
            if result is not None:
                break
        self.assertIsInstance(result, Choke)

    @async_test
    async def test_interested(self):
        reader = Reader([b'\x00\x00\x00\x01\x02'])
        buffer = b''
        result = None
        async for message in PeerStreamIterator(reader, buffer):
            result = message
            if result is not None:
                break
        self.assertIsInstance(result, Interested)

    @async_test
    async def test_not_interested(self):
        reader = Reader([b'\x00\x00\x00\x01\x03'])
        buffer = b''
        result = None
        async for message in PeerStreamIterator(reader, buffer):
            result = message
            if result is not None:
                break
        self.assertIsInstance(result, NotInterested)

    @async_test
    async def test_have(self):
        reader = Reader([b'\x00\x00\x00\x05\x04\x00\x00\x00\x04'])
        buffer = b''
        result = None
        async for message in PeerStreamIterator(reader, buffer):
            result = message
            if result is not None:
                break
        self.assertIsInstance(result, Have)

    @async_test
    async def test_request(self):
        reader = Reader([b'\x00\x00\x00\r\x06\x00\x00\x00\x00'
                         b'\x00\x00\x00\x00\x00\x00@\x00'])
        buffer = b''
        result = None
        async for message in PeerStreamIterator(reader, buffer):
            result = message
            if result is not None:
                break
        self.assertIsInstance(result, Request)
