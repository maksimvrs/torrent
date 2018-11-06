import unittest
import asyncio
from src.tracker import Tracker
from src.info import Info


class TrackerTestCase(unittest.TestCase):

    def test_tracker(self):
        info = Info("/Users/maksim/Downloads/ubuntu.iso.torrent")

        async def test_tracker_async(info):
            tracker = Tracker(info)
            response = await tracker.connect(True, 0, 0)
            print(response.peers)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.wait([asyncio.ensure_future(test_tracker_async(info))]))
        loop.close()
