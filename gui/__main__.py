import sys

from PyQt5 import QtWidgets

from gui import ClientGUI


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    client_gui = ClientGUI()
    client_gui.show()
    sys.exit(app.exec_())
