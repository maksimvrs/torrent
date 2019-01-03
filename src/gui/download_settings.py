from PyQt5 import QtWidgets, QtCore


class FileWidget(QtWidgets.QWidget):
    def __init__(self, name, parent=None):
        super(FileWidget, self).__init__(parent)
        self.layout = QtWidgets.QHBoxLayout()

        self.name = name

        file = QtWidgets.QLabel(self.name)
        self.layout.addWidget(file, QtCore.Qt.AlignLeft)

        self.check_box = QtWidgets.QCheckBox()
        self.check_box.setChecked(True)
        self.layout.addWidget(self.check_box)
        self.layout.setAlignment(self.check_box, QtCore.Qt.AlignRight)

        self.setLayout(self.layout)


class DownloadSettings(QtWidgets.QWidget):
    opened = QtCore.pyqtSignal()
    canceled = QtCore.pyqtSignal()

    def __init__(self, info, parent=None):
        super(DownloadSettings, self).__init__(parent)
        self._files = []

        self.info = info

        self.layout = QtWidgets.QVBoxLayout()

        # List for change files
        self.files_list = QtWidgets.QListWidget(self)
        self.layout.addWidget(self.files_list)

        change_file_layout = QtWidgets.QHBoxLayout()
        change_file_layout.addWidget(QtWidgets.QLabel("Скачивать в "))
        self._path = QtWidgets.QLineEdit()
        path_list = QtCore.QStandardPaths.standardLocations(QtCore.QStandardPaths.DownloadLocation)
        if path_list:
            self._path.setText(path_list[0])
        else:
            self._path.setText('/')
        self.open_path_button = QtWidgets.QPushButton("Выбрать папку")
        self.open_path_button.clicked.connect(
            lambda: self._path.setText(self._get_download_path()))
        change_file_layout.addWidget(self._path)
        change_file_layout.addWidget(self.open_path_button)
        self.layout.addLayout(change_file_layout)

        buttons_layout = QtWidgets.QHBoxLayout()
        self.ok = QtWidgets.QPushButton("Ок")
        self.ok.clicked.connect(self.opened)
        self.ok.clicked.connect(self.close)
        self.cancel = QtWidgets.QPushButton("Отмена")
        self.cancel.clicked.connect(self.canceled)
        self.cancel.clicked.connect(self.close)
        buttons_layout.addWidget(self.ok)
        buttons_layout.addWidget(self.cancel)
        self.layout.addLayout(buttons_layout)

        self.setLayout(self.layout)

        self.setGeometry(0, 0, 500, 300)

    @property
    def files(self):
        return [i for i, file in enumerate(self._files) if file.check_box.isChecked()]

    @property
    def path(self):
        return self._path.text() if self._path.text()[-1] == '/' else self._path.text() + '/'

    def open(self):
        self.show()
        if self.info.is_multi_file:
            for file in self.info.files:
                listWidgetItem = QtWidgets.QListWidgetItem(self.files_list)
                self._files.append(FileWidget('/'.join(file['path'])))
                listWidgetItem.setSizeHint(self._files[-1].sizeHint())
                self.files_list.setItemWidget(listWidgetItem, self._files[-1])
                self.files_list.addItem(listWidgetItem)
        else:
            listWidgetItem = QtWidgets.QListWidgetItem(self.files_list)
            self._files.append(FileWidget(self.info.name))
            listWidgetItem.setSizeHint(self._files[-1].sizeHint())
            self.files_list.setItemWidget(listWidgetItem, self._files[-1])
            self.files_list.addItem(listWidgetItem)

    def _get_download_path(self):
        download_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Выберите папку для загрузки", self.path)
        if download_path:
            return download_path
        return self._path.text()
