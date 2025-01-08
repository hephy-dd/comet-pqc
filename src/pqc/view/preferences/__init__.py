from typing import Optional

from PyQt5 import QtWidgets

from .resources import ResourcesWidget
from .options import OptionsWidget
from .table import TableWidget

__all__ = ["PreferencesDialog"]


class PreferencesDialog(QtWidgets.QDialog):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preferences")

        self.tabWidget = QtWidgets.QTabWidget(self)

        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.tabWidget)
        layout.addWidget(self.buttonBox)

        # Register tabs

        self.resourcesWidget = ResourcesWidget(self)
        self.addTab(self.resourcesWidget, "Resources")

        self.tableWidget = TableWidget(self)
        self.addTab(self.tableWidget, "Table")

        self.optionsWidget = OptionsWidget(self)
        self.addTab(self.optionsWidget, "Options")

    def addTab(self, widget: QtWidgets.QWidget, title: str) -> None:
        self.tabWidget.addTab(widget, "Resources")

    def writeSettings(self) -> None:
        for index in range(self.tabWidget.count()):
            widget = self.tabWidget.widget(index)
            if hasattr(widget, "writeSettings"):
                widget.writeSettings()
        QtWidgets.QMessageBox.information(self, "Restart Required", "Application restart required for some changes to take effect.")

    def readSettings(self) -> None:
        for index in range(self.tabWidget.count()):
            widget = self.tabWidget.widget(index)
            if hasattr(widget, "readSettings"):
                widget.readSettings()
