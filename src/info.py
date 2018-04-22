#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from bencode import bencode, bdecode
import hashlib


class Info(object):

    def __init__(self, file_name):
        self.file_name = file_name
        try:
            with open(self.file_name, 'rb') as file:
                self.data = bdecode(file.read())
        except EOFError:
            pass
        self.announce = self.data[b'announce'].decode()
        self.announce_list = [x[0].decode() for x in self.data[b'announce-list']]
        self.length = int(self.data[b'info'][b'length'])
        self.name = self.data[b'info'][b'name'].decode()
        self.encoding = self.data[b'encoding'].decode()
        self.hash = hashlib.sha1(bencode(self.data[b'info'])).hexdigest()
