#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import asyncio
import logging
import time
from time import sleep
from PyQt5.QtWidgets import (QApplication, QWidget,
                             QVBoxLayout, QHBoxLayout,
                             QGridLayout, QPushButton,
                             QLineEdit, QLabel)
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

from src.client import TorrentClient
from src.info import Info


class ClientThread(QThread):
    signal = pyqtSignal()

    logging.basicConfig(level=logging.DEBUG)

    def __init__(self, file, parent=None):
        QThread.__init__(self, parent)
        self.file = file
        self.info = Info(file)
        self.client = None

    async def run_async(self):
        self.client = TorrentClient(self.info)
        await self.client.start()

    def run(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.run_async())


class TorrentGUI(QWidget):

    def __init__(self):
        QWidget.__init__(self)
        self.peer_state = QVBoxLayout()
        self.clients = []

        # Init GUI
        self.setGeometry(300, 300, 300, 220)
        self.setWindowTitle('Torrent')
        file_layout = QHBoxLayout()
        file_input = QLineEdit()
        file_layout.addWidget(file_input)
        start_button = QPushButton("Start")
        start_button.clicked.connect(lambda: self.start(file_input.text()))
        file_layout.addWidget(start_button)
        layout = QVBoxLayout()
        layout.addLayout(self.peer_state)
        layout.addLayout(file_layout)
        self.setLayout(layout)
        self.show()

    def start(self, file=None):
        client = ClientThread(file)
        client.signal.connect(lambda message: print(message))
        self.clients.append(client)
        client.start()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = TorrentGUI()
    sys.exit(app.exec_())
