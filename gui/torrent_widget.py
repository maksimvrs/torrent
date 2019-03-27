from PyQt5 import QtWidgets, QtGui, QtCore

from gui import ClientThread


class TorrentWidget(QtWidgets.QWidget):
    error = QtCore.pyqtSignal(['QString'])

    def __init__(self, client_thread, parent=None):
        super(TorrentWidget, self).__init__(parent)

        if not isinstance(client_thread, ClientThread):
            raise TypeError(
                "Type of torrent_client is invalide. Must be a ClientThread.")

        self.client_thread = client_thread
        self.client_thread.bytesDownloadedChanged.connect(self.update_status)
        self.client_thread.error.connect(self.error)

        layout = QtWidgets.QHBoxLayout(self)

        self.icon_label = QtWidgets.QLabel(self)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setSpacing(0)

        label = QtWidgets.QLabel(client_thread.info.name)
        main_layout.addWidget(label)

        self.progress_info = QtWidgets.QLabel()

        progress_info_font = QtGui.QFont()
        progress_info_font.setPixelSize(12)
        self.progress_info.setFont(progress_info_font)
        main_layout.addWidget(self.progress_info, QtCore.Qt.AlignLeft)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setTextVisible(True)
        main_layout.addWidget(self.progress_bar, QtCore.Qt.AlignHCenter)

        layout.addWidget(self.icon_label)
        layout.addLayout(main_layout, QtCore.Qt.AlignLeft)

        self.setLayout(layout)

    def update_status(self):
        self.progress_info.setText('{downloaded} MB from {size} MB\
            ({percent}%) {speed} KB/S'.format(
            downloaded=round(self.client_thread.downloaded / 2 ** 20, 2),
            size=round(self.client_thread.size / 2 ** 20, 2),
            percent=round(self.client_thread.percent, 2),
            speed=round(self.client_thread.speed / 2 ** 10, 2)))
        self.progress_bar.setValue(self.client_thread.percent)

    def update_icon(self):
        file_icon_provider = QtWidgets.QFileIconProvider()
        icon = file_icon_provider.icon(QtCore.QFileInfo(
            self.client_thread.work_path + self.client_thread.info.name))
        pixmap = icon.pixmap(QtCore.QSize(36, 36))
        self.icon_label.setPixmap(pixmap)
