#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import asyncio
import logging

from concurrent.futures import CancelledError

from src.client import TorrentClient
from src.info import Info


async def start(info):
    client = TorrentClient(info)
    await client.start()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('torrent',
                        help='the .torrent to download')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='enable verbose output')

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.wait([asyncio.ensure_future(start(Info(args.torrent)))]))
        loop.close()

    except CancelledError:
        logging.warning('Event loop was canceled')


if __name__ == '__main__':
    main()