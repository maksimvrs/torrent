import asyncio

from PyQt5 import QtCore, QtWidgets

from src.torrent_client import TorrentClient
from src.info import Info


class ClientThread(QtCore.QThread):
    clientStarted = QtCore.pyqtSignal()
    bytesDownloadedChanged = QtCore.pyqtSignal()
    speedChanged = QtCore.pyqtSignal()
    clientCreated = QtCore.pyqtSignal()
    error = QtCore.pyqtSignal(['QString'])

    def __init__(self, file, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.file = file
        self.files = None
        self.work_path = '~/'
        self.info = Info(file)
        self.client = None

    async def run_async(self):
        self.client = TorrentClient(self.info, self.files, self.work_path)
        self.client.piece_manager.bytes_downloaded_changed = self.bytes_downloaded_changed
        self.clientCreated.emit()
        try:
            await self.client.start()
        except Exception as e:
            self.error.emit(str(e))

    def run(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.run_async())

    def bytes_downloaded_changed(self):
        self.bytesDownloadedChanged.emit()

    def speed_changed(self):
        self.speedChanged.emit()

    @property
    def downloaded(self):
        return self.client.piece_manager.bytes_downloaded

    @property
    def size(self):
        if self.info.is_multi_file:
            return sum(map(lambda x: x['length'], self.clientThread.info.files))
        else:
            return self.info.length

    @property
    def percent(self):
        return self.downloaded / self.size * 100

    @property
    def speed(self):
        return self.client.speed
