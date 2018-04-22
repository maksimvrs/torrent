#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from info import Info


class Torrent(object):

    def __init__(self, file):
        self.info = Info(file)
