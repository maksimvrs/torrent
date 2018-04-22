#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from info import Info
from announce import Announce


class Torrent(object):

    def __init__(self, file):
        self.info = Info(file)
        self.announce = Announce(self.info)
        self.announce.request()
