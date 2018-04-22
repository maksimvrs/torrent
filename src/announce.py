#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import requests
from string import ascii_letters, digits
from bencode import bencode, bdecode

VERSION = '0001'
PORT = 6969


class Announce(object):

    def __init__(self, info):
        self.info = info
        self.request_params = {'info_hash': self.info.hash,
                               'peer_id': ('-DR' + VERSION + ''.join(random.sample(ascii_letters + digits, 13))),
                               'peer_id': "-PC0001-706887310628",
                               'port': PORT,
                               'uploaded': 0,
                               'downloaded': 0,
                               'left': self.info.length,
                               'compact': 1,
                               'supportcrypto': 1,
                               'event': 'started'}
        self.response = {}
        self.peers = []

    def request(self):
        trackers = [x for x in self.info.announce_list if x.startswith("http")]
        for tracker in reversed(trackers):
            try:
                self.response = bdecode(requests.get(tracker, self.request_params).content)
                break
            except requests.exceptions.ConnectionError as error:
                print(tracker + " ERROR")
                print(error.request.url)
                continue
        self.response = bdecode(b'd8:intervali1800e5:peers6:\xb0;\xc9\x12\x1b9e')
        peers_raw = self.response[b'peers']
        while len(peers_raw) >= 6:
            peer = ((".".join(map(str, peers_raw[0:4])),
                     int.from_bytes(peers_raw[4:6], 'big')))
            if peer not in self.peers:
                self.peers.append(peer)
            peers_raw = peers_raw[6:]

