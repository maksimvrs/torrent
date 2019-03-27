import asyncio
import logging
import sys
import signal

import click

from src.torrent_client import TorrentClient
from src.info import Info

logging.basicConfig(level=logging.CRITICAL)


client = None
info = None


async def start(file, work_path):
    global info
    global client
    info = Info(file)
    files = [i for i in range(len(info.files))] if info.is_multi_file else [0]
    client = TorrentClient(info, files, work_path)
    client.piece_manager.bytes_downloaded_changed = bytes_downloaded_changed
    await client.start()


def bytes_downloaded_changed():
    size = sum(map(lambda x: x['length'], info.files)) if info.is_multi_file else info.length
    sys.stdout.write('\rDownloaded {downloaded} MB from {size} MB ({percent}%) {speed} KB/S'.format(
            downloaded=round(client.piece_manager.bytes_downloaded / 2 ** 20, 2),
            size=round(size / 2 ** 20, 2),
            percent=round(client.piece_manager.bytes_downloaded / size * 100, 2),
            speed=round(client.speed / 2 ** 10, 2)))
    sys.stdout.flush()


def signal_handler(sig, frame):
    print("\nWait...")
    loop = asyncio.get_event_loop()
    loop.create_task(client.stop())
    exit(0)


@click.command()
@click.option('--file', help='.torrent file for download')
@click.option('--path', help='Path for download')
def main(file, path):
    """Simple torrent client"""
    if file is None or path in None:
        with click.Context(main) as ctx:
            click.echo(main.get_help(ctx))
        return
    loop = asyncio.new_event_loop()
    loop.run_until_complete(start(file, path))
    loop.close()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    main()
