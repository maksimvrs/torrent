#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import asyncio
import logging
import time
from time import sleep

from PyQt5 import QtGui, QtWidgets, QtCore

from src.client import TorrentClient
from src.info import Info


class ClientThread(QtCore.QThread):
    signal = QtCore.pyqtSignal()
    bytesDownloadedChanged = QtCore.pyqtSignal(int, name='bytesDownloadedChanged')

    logging.basicConfig(level=logging.DEBUG)

    def __init__(self, file, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.file = file
        self.info = Info(file)
        self.client = None

    async def run_async(self):
        self.client = TorrentClient(self.info)
        self.client.piece_manager.bytes_downloaded_changed = self.bytes_downloaded_changed
        await self.client.start()

    def run(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.run_async())

    def bytes_downloaded_changed(self):
        if self.client.info.length != 0:
            print("bytes_downloaded_changed", self.client.piece_manager.bytes_downloaded / self.client.info.length * 100)
            self.bytesDownloadedChanged.emit(self.client.piece_manager.bytes_downloaded / self.client.info.length * 100)


class PeersWidget(QtWidgets.QListWidget):
    def __init__(self, clientThread, parent=None):
        super(PeersWidget, self).__init__(parent)
        self.clientThread = clientThread
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.updatePeers)
        self.timer.start(1000)

    @QtCore.pyqtSlot()
    def updatePeers(self):
        self.clear()
        self.addItems([', '.join(state) for state in self.clientThread.client.peers.my_state if state])


class TorrentWidget(QtWidgets.QWidget):
    def __init__(self, clientThread, parent=None):
        super(TorrentWidget, self).__init__(parent)

        if not isinstance(clientThread, ClientThread):
            raise TypeError("Type of torrent_client is invalide. Must be a ClientThread.")

        self.clientThread = clientThread

        layout = QtWidgets.QHBoxLayout(self)

        fileIconProvider = QtWidgets.QFileIconProvider()
        icon = fileIconProvider.icon(QtCore.QFileInfo(clientThread.info.name))
        pixmap = icon.pixmap(QtCore.QSize(36, 36))
        self.iconLabel = QtWidgets.QLabel(self)
        self.iconLabel.setPixmap(pixmap)

        mainLayout = QtWidgets.QVBoxLayout()
        mainLayout.setSpacing(0)

        self.label = QtWidgets.QLabel(clientThread.info.name)
        mainLayout.addWidget(self.label)

        self.progress = QtWidgets.QProgressBar(self)
        self.progress.setTextVisible(True)
        self.clientThread.bytesDownloadedChanged.connect(lambda x: self.progress.setValue(x))
        mainLayout.addWidget(self.progress, QtCore.Qt.AlignHCenter)

        layout.addWidget(self.iconLabel)
        layout.addLayout(mainLayout, QtCore.Qt.AlignLeft)

        self.setLayout(layout)


class TorrentGUI(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super(TorrentGUI, self).__init__(parent)
        self.torrents = []
        self.setAcceptDrops(True)
        # Init GUI
        self.setGeometry(300, 300, 300, 220)
        self.setWindowTitle('Torrent')

        # Toolbar
        tab_bar = self.addToolBar("File")
        action_new = QtWidgets.QAction("New", self)
        tab_bar.addAction(action_new)
        action_open = QtWidgets.QAction("Open", self)
        tab_bar.addAction(action_open)
        action_save = QtWidgets.QAction("Remove", self)
        tab_bar.addAction(action_save)
        tab_bar.actionTriggered[QtWidgets.QAction].connect(self.toolBarAction)

        # ListView
        self.torrents_list = QtWidgets.QListWidget(self)

        # Layout
        self.setCentralWidget(self.torrents_list)

    def addTorrent(self, file_name):
        torrentWidget = TorrentWidget(file_name)
        listWidgetItem = QtWidgets.QListWidgetItem(self.torrents_list)
        listWidgetItem.setSizeHint(torrentWidget.sizeHint())
        self.torrents_list.addItem(listWidgetItem)
        self.torrents_list.setItemWidget(listWidgetItem, torrentWidget)

    def toolBarAction(self, action):
        print(action.text())
        if action.text() == "New":
            file_name = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', '~', "Torrent(*.torrent)")[0]
            self.start(file_name)
            # print(file_name)
            # self.start(file_name)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            links = []
            for url in event.mimeData().urls():
                links.append(str(url.toLocalFile()))
                self.start(str(url.toLocalFile()))
            print(links)
            # self.emit(QtCore.SIGNAL("dropped"), links)
        else:
            event.ignore()

    def start(self, file):
        try:
            clientThread = ClientThread(file)
        except (OSError, IOError) as e:
            print(e)
            return
        clientThread.signal.connect(lambda message: print(message))

        torrentWidget = TorrentWidget(clientThread)
        listWidgetItem = QtWidgets.QListWidgetItem(self.torrents_list)
        listWidgetItem.setSizeHint(torrentWidget.sizeHint())
        self.torrents_list.addItem(listWidgetItem)
        self.torrents_list.setItemWidget(listWidgetItem, torrentWidget)

        peersWidget = PeersWidget(clientThread)
        peersWidget.show()

        clientThread.start()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    torrent_gui = TorrentGUI()
    torrent_gui.show()
    sys.exit(app.exec_())
