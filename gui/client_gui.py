import logging

from PyQt5 import QtWidgets, QtCore

from gui import ClientThread
from gui import TorrentWidget
from gui import DownloadSettings


class ClientGUI(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(ClientGUI, self).__init__(parent)
        self.torrents = []
        self.setAcceptDrops(True)
        # Init GUI
        screen_width = QtWidgets.QApplication.desktop().screenGeometry().width()
        screen_height = QtWidgets.QApplication.desktop().screenGeometry().height()
        width = 500
        height = 300
        self.setGeometry((screen_width - width) / 2, (screen_height - height) / 2, width, height)
        self.setWindowTitle('Torrent')

        # Toolbar
        tab_bar = self.addToolBar("File")
        action_new = QtWidgets.QAction("New", self)
        tab_bar.addAction(action_new)
        action_open = QtWidgets.QAction("Open", self)
        tab_bar.addAction(action_open)
        action_save = QtWidgets.QAction("Remove", self)
        tab_bar.addAction(action_save)
        tab_bar.actionTriggered[QtWidgets.QAction].connect(self.tool_bar_action)

        # ListView
        self.torrents_list = QtWidgets.QListWidget(self)

        self.download_settings = None

        self.client_thread = None

        # Layout
        self.setCentralWidget(self.torrents_list)

    def tool_bar_action(self, action):
        if action.text() == "New":
            default_path = '~/'
            path_list = QtCore.QStandardPaths.standardLocations(QtCore.QStandardPaths.HomeLocation)
            if path_list:
                default_path = path_list[0]
            file_name = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', default_path, "Torrent(*.torrent)")[0]
            self.open(file_name)
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
                self.open(str(url.toLocalFile()))
            # print(links)
            # self.emit(QtCore.SIGNAL("dropped"), links)
        else:
            event.ignore()

    def open(self, file):
        try:
            self.client_thread = ClientThread(file)
            # self.client_thread.error.connect(self.error)
        except (OSError, IOError) as e:
            logging.debug(e)
            return

        self.download_settings = DownloadSettings(self.client_thread.info)
        self.download_settings.opened.connect(self.start)
        self.download_settings.open()

    def start(self):
        torrentWidget = TorrentWidget(self.client_thread)
        torrentWidget.error.connect(self.error)
        self.client_thread.files = self.download_settings.files
        self.client_thread.work_path = self.download_settings.path
        self.client_thread.clientCreated.connect(torrentWidget.update_icon)

        listWidgetItem = QtWidgets.QListWidgetItem(self.torrents_list)
        listWidgetItem.setSizeHint(torrentWidget.sizeHint())
        self.torrents_list.addItem(listWidgetItem)
        self.torrents_list.setItemWidget(listWidgetItem, torrentWidget)
        self.torrents.append([listWidgetItem, torrentWidget])

        self.client_thread.start()

    def error(self, message):
        QtWidgets.QMessageBox.critical(self, 'Error', message)
        for i in self.torrents:
            if i[1] == self.sender():
                self.torrents_list.removeItemWidget(i[0])

