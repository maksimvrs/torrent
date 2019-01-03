import binascii

import aiohttp
import asyncio
import logging
import socket
from struct import unpack
import urllib.parse
import btdht

from src import bencoding


dht = btdht.DHT()


class TrackerResponse:
    """
    The response from the tracker after a successful connection to the
    trackers announce URL.
    Even though the connection was successful from a network point of view,
    the tracker might have returned an error (stated in the `failure`
    property).
    """

    def __init__(self, response: dict):
        self.response = response

    @property
    def failure(self):
        """
        If this response was a failed response, this is the error message to
        why the tracker request failed.
        If no error occurred this will be None
        """
        if b'failure reason' in self.response:
            return self.response[b'failure reason'].decode('utf-8')
        return None

    @property
    def interval(self) -> int:
        """
        Interval in seconds that the client should wait between sending
        periodic requests to the tracker.
        """
        return self.response.get(b'interval', 0)

    @property
    def complete(self) -> int:
        """
        Number of peers with the entire file, i.e. seeders.
        """
        return self.response.get(b'complete', 0)

    @property
    def incomplete(self) -> int:
        """
        Number of non-seeder peers, aka "leechers".
        """
        return self.response.get(b'incomplete', 0)

    @property
    def peers(self):
        """
        A list of tuples for each peer structured as (ip, port)
        """
        # The BitTorrent specification specifies two types of responses. One
        # where the peers field is a list of dictionaries and one where all
        # the peers are encoded in a single string
        peers = self.response[b'peers']
        if type(peers) == list:
            # TODO Implement support for dictionary peer list
            logging.debug('Dictionary model peers are returned by tracker')
            raise NotImplementedError()
        else:
            logging.debug('Binary model peers are returned by tracker')

            # Split the string in pieces of length 6 bytes, where the first
            # 4 characters is the IP the last 2 is the TCP port.
            peers = [peers[i:i + 6] for i in range(0, len(peers), 6)]

            # Convert the encoded address to a list of tuples
            return [(socket.inet_ntoa(p[:4]), _decode_port(p[4:]))
                    for p in peers]

    def __str__(self):
        return "incomplete: {incomplete}\n" \
               "complete: {complete}\n" \
               "interval: {interval}\n" \
               "peers: {peers}\n".format(
            incomplete=self.incomplete,
            complete=self.complete,
            interval=self.interval,
            peers=", ".join([x for (x, _) in self.peers]))


class Tracker:
    """
    Represents the connection to a tracker for a given Torrent that is either
    under download or seeding state.
    """

    def __init__(self, info):
        self.info = info
        self.session = aiohttp.ClientSession()

    @staticmethod
    async def connect_dht():
        dht.start()
        await asyncio.sleep(15)
        return dht.get_peers(binascii.a2b_hex("0403fb4728bd788fbcb67e87d6feb241ef38c75a"))

    async def connect(self,
                      first: bool = None,
                      uploaded: int = 0,
                      downloaded: int = 0):
        """
        Makes the announce call to the tracker to update with our statistics
        as well as get a list of available peers to connect to.
        If the call was successful, the list of peers will be updated as a
        result of calling this function.
        :param first: Whether or not this is the first announce call
        :param uploaded: The total number of bytes uploaded
        :param downloaded: The total number of bytes downloaded
        """
        params = {
            'info_hash': self.info.hash20,
            'peer_id': self.info.peer_id,
            'port': 6889,
            'uploaded': uploaded,
            'downloaded': downloaded,
            'left': self.info.length - downloaded,
            'compact': 1}
        if first:
            params['event'] = 'started'

        url = self.info.announce + '?' + urllib.parse.urlencode(params)
        logging.info('Connecting to tracker at: ' + url)

        try:
            async with self.session.get(url) as response:
                if not response.status == 200:
                    raise ConnectionError('Unable to connect to tracker')
                data = await response.read()
                return TrackerResponse(bencoding.Decoder(data).decode())
        except Exception as e:
            logging.error(e)
        return None

    async def close(self):
        await self.session.close()

    def _construct_tracker_parameters(self):
        """
        Constructs the URL parameters used when issuing the announce call
        to the tracker.
        """
        return {
            'info_hash': self.info.info_hash,
            'peer_id': self.info.peer_id,
            'port': 6889,
            # TODO Update stats when communicating with tracker
            'uploaded': 0,
            'downloaded': 0,
            'left': 0,
            'compact': 1}


def _decode_port(port):
    """
    Converts a 32-bit packed binary port number to int
    """
    # Convert from C style big-endian encoded as unsigned short
    return unpack(">H", port)[0]
