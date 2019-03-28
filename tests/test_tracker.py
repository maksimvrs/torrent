import asyncio
import unittest

from src.tracker import Tracker, TrackerResponse
from src.info import Info


class TrackerTests(unittest.TestCase):
    def async_test(f):
        def wrapper(*args, **kwargs):
            coro = asyncio.coroutine(f)
            future = coro(*args, **kwargs)
            loop = asyncio.get_event_loop()
            loop.run_until_complete(future)

        return wrapper

    @async_test
    async def test_good_tracker(self):
        info = Info('./data/ubuntu-18.iso.torrent')
        tracker = Tracker(info)
        result = await tracker.connect(0, 0, 0)
        await tracker.close()
        self.assertTrue(result.failure is None)
        print(result)

    @async_test
    async def test_bad_tracker(self):
        info = Info('./data/ubuntu.iso.torrent')
        tracker = Tracker(info)
        result = await tracker.connect(0, 0, 0)
        await tracker.close()
        self.assertFalse(result.failure is None)
        print(result)
