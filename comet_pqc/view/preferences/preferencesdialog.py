from PyQt5 import QtCore, QtWidgets

from ..components import showInfo

__all__ = ["PreferencesDialog"]


class PreferencesWidget(QtWidgets.QWidget):

    def readSettings(self):
        ...

    def writeSettings(self):
        ...


class PreferencesDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")

        self.tabWidget = QtWidgets.QTabWidget(self)

        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.showNotice)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.tabWidget)
        layout.addWidget(self.buttonBox)

    @QtCore.pyqtSlot()
    def showNotice(self) -> None:
        title = "Notice"
        text = "Application restart required for changes to take effect."
        QtWidgets.QMessageBox.information(self, title, text)

    def addTab(self, widget: QtWidgets.QWidget, text: str) -> None:
        self.tabWidget.addTab(widget, text)

    def insertTab(self, index: int,  widget: QtWidgets.QWidget, text: str) -> None:
        self.tabWidget.insertTab(index, widget, text)

    def readSettings(self) -> None:
        for index in range(self.tabWidget.count()):
            widget = self.tabWidget.widget(index)
            if isinstance(widget, PreferencesWidget):
                widget.readSettings()

    def writeSettings(self) -> None:
        for index in range(self.tabWidget.count()):
            widget = self.tabWidget.widget(index)
            if isinstance(widget, PreferencesWidget):
                widget.writeSettings()
