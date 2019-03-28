import asyncio
import unittest
from asyncio import Queue

from src.torrent_client import PieceManager
from src.tracker import Tracker, TrackerResponse
from src.info import Info
from src.peer import PeerConnection


class PeerTests(unittest.TestCase):
    def async_test(f):
        def wrapper(*args, **kwargs):
            coro = asyncio.coroutine(f)
            future = coro(*args, **kwargs)
            loop = asyncio.get_event_loop()
            loop.run_until_complete(future)

        return wrapper

    def block_received(self, peer_id, piece_index, block_offset, data):
        pass

    @async_test
    async def test_peer(self):
        info = Info('./data/ubuntu-18.iso.torrent')
        tracker = Tracker(info)
        result = await tracker.connect(0, 0, 0)
        await tracker.close()

        available_peers = Queue()
        piece_manager = PieceManager(info, [1], './data/')

        peer_connection = PeerConnection(available_peers,
                                         info.hash20,
                                         info.peer_id,
                                         piece_manager,
                                         self.block_received)

        await available_peers.put(result.peers[0])

        await asyncio.sleep(15)

        print(peer_connection.my_state)
