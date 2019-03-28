import asyncio
import unittest
from asyncio import Queue

from src.peer_streem_iterator import PeerStreamIterator
from src.torrent_client import PieceManager
from src.tracker import Tracker, TrackerResponse
from src.info import Info
from src.peer import PeerConnection


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
    async def test_one_peer(self):
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
                         b'\xff\xff\xff\xff\xf0',
                         b'\x00\x00\x00\x01\x01'])
        buffer = list()
        result = list()
        async for message in PeerStreamIterator(reader, buffer):
            result.append(str(message))
            if len(result) >= 2:
                break
        self.assertListEqual(result, ['BitField', 'Unchoke'])
