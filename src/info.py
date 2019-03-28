#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import random
import datetime
from string import ascii_letters, digits

from src.bencoding import Decoder, Encoder

PREFIX = '-DR'
VERSION = '0001'


class Info(object):
    """

    """

    def __init__(self, file_name):
        self.file_name = file_name

        with open(self.file_name, 'rb') as file:
            self.data = Decoder(file.read()).decode()

        if b'announce' not in self.data:
            raise AttributeError(
                "The torrent file does not have an attribute announce")

        self.__metainfo__ = self.data.get(b'info')
        self.check_integrity()

        self.peer_id = (PREFIX + VERSION
                        + ''.join(random.sample(ascii_letters + digits, 13)))

        info_raw = Encoder(self.__metainfo__).encode()
        hash_raw = hashlib.sha1(info_raw)
        self.hash40 = hash_raw.hexdigest()
        self.hash20 = hash_raw.digest()

    def check_integrity(self):
        if not self.__metainfo__:
            raise AttributeError(
                "The torrent file does not have an attribute info")
        if b'piece length' not in self.__metainfo__:
            raise AttributeError(
                "The torrent file does not have an attribute piece length")
        if b'pieces' not in self.__metainfo__:
            raise AttributeError(
                "The torrent file does not have an attribute pieces")
        if b'name' not in self.__metainfo__:
            raise AttributeError(
                "The torrent file does not have an attribute name")
        if b'length' not in self.__metainfo__ and \
           b'files' not in self.__metainfo__:
            raise AttributeError(
                "The torrent file does not have an attribute length or files")
        # if b'files' in self.__metainfo__:
        #     if b'length' not in self.__metainfo__[b'files']:
        #         raise AttributeError(
        #           "The torrent file does not have an attribute length")
        #     if b'name' not in self.__metainfo__[b'files']:
        #         raise AttributeError(
        #           "The torrent file does not have an attribute path")

    @property
    def announce(self) -> str:
        return self.data[b'announce'].decode('utf-8')

    @property
    def announce_list(self) -> str:
        return [i[0].decode('utf-8') for i in self.data.get(b'announce-list')]

    @property
    def comment(self) -> str:
        return self.data.get(b'comment').decode('utf-8')

    @property
    def is_multi_file(self) -> bool:
        return b'files' in self.__metainfo__

    @property
    def creation_date(self) -> datetime:
        return datetime.fromtimestamp(self.data.get(b'creation date'))

    @property
    def created_by(self) -> str:
        return self.data.get(b'created by').decode('utf-8')

    @property
    def encoding(self) -> str:
        return self.data.get(b'encoding').decode('utf-8')

    # Info section:
    @property
    def piece_length(self) -> int:
        return self.__metainfo__[b'piece length']

    @property
    def pieces(self) -> list:
        return [self.__metainfo__[b'pieces'][i:i + 20]
                for i in range(0, len(self.__metainfo__[b'pieces']), 20)]

    @property
    def private(self) -> bool:
        return self.__metainfo__[b'private'] == 1

    @property
    def name(self) -> str:
        return self.__metainfo__[b'name'].decode('utf-8')

    @property
    def length(self):
        if self.is_multi_file:
            return sum([i[b'length'] for i in self.__metainfo__[b'files']])
        return self.__metainfo__[b'length']

    @property
    def files(self) -> list:
        return [{'length': file[b'length'],
                 'path': [path.decode()
                          for path in file[b'path']]}
                for file in self.__metainfo__[b'files']]

    @property
    def md5sum(self) -> str:
        return self.__metainfo__[b'files'].get(b'md5sum')

    @property
    def path(self) -> str:
        return self.__metainfo__[b'files'].get(b'path')
