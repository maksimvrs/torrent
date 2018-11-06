import unittest
import asyncio
from src.info import Info
from src.client import TorrentClient
import logging

logging.basicConfig(level=logging.DEBUG)


class ClientTestCase(unittest.TestCase):

    def test_client(self):
        info = Info("/Users/maksim/Downloads/ubuntu.iso.torrent")

        async def start():
            client = TorrentClient(info)
            await client.start()

        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.wait([asyncio.ensure_future(start())]))
        loop.close()
