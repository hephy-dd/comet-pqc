from PyQt5 import QtCore, QtWidgets

from .preferencesdialog import PreferencesDialog as _PreferencesDialog
from .resourceswidget import ResourcesWidget
from .optionswidget import OptionsWidget
from .tablewidget import TableWidget

__all__ = ["PreferencesDialog"]


class PreferencesDialog:  # TODO

    def __init__(self, parent=None) -> None:
        self._dialog = _PreferencesDialog(parent)
        self._dialog.addTab(ResourcesWidget(), "Resources")
        self._dialog.addTab(TableWidget(), "Table")
        self._dialog.addTab(OptionsWidget(), "Options")

    def readSettings(self) -> None:
        settings = QtCore.QSettings()
        geometry = settings.value("preferences/geometry", QtCore.QByteArray(), QtCore.QByteArray)
        if not self._dialog.restoreGeometry(geometry):
            self._dialog.resize(800, 600)

    def writeSettings(self) -> None:
        settings = QtCore.QSettings()
        geometry = self._dialog.saveGeometry()
        settings.setValue("preferences/geometry", geometry)

    def exec(self):
        self._dialog.readSettings()
        self._dialog.exec()
        if self._dialog.result() == QtWidgets.QDialog.Accepted:
            self._dialog.writeSettings()
