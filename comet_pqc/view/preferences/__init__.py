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

        self.resourcesWidget = ResourcesWidget(self)
        self.tabWidget.addTab(self.resourcesWidget, "Resources")

        self.tableWidget = TableWidget(self)
        self.tabWidget.addTab(self.tableWidget, "Table")

        self.optionsWidget = OptionsWidget(self)
        self.tabWidget.addTab(self.optionsWidget, "Options")

        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.tabWidget)
        layout.addWidget(self.buttonBox)

    def writeSettings(self) -> None:
        for index in range(self.tabWidget.count()):
            widget = self.tabWidget.widget(index)
            widget.writeSettings()
        QtWidgets.QMessageBox.information(self, "Restart Required", "Application restart required for some changes to take effect.")

    def readSettings(self) -> None:
        for index in range(self.tabWidget.count()):
            widget = self.tabWidget.widget(index)
            widget.readSettings()
