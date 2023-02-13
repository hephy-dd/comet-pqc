from comet.ui.preferences import PreferencesDialog as _PreferencesDialog
from PyQt5 import QtCore, QtWidgets

from .options import OptionsTab
from .table import TableTab
from .webapi import WebAPITab

__all__ = ["PreferencesDialog"]


class PreferencesDialog:

    def __init__(self, parent=None) -> None:
        self._dialog = _PreferencesDialog()

        table_tab = TableTab()
        self._dialog.tab_widget.append(table_tab)
        self._dialog.table_tab = table_tab

        webapi_tab = WebAPITab()
        self._dialog.tab_widget.append(webapi_tab)
        self._dialog.webapi_tab = webapi_tab

        options_tab = OptionsTab()
        self._dialog.tab_widget.append(options_tab)
        self._dialog.options_tab = options_tab

    def readSettings(self) -> None:
        settings = QtCore.QSettings()
        geometry = settings.value("preferences/geometry", QtCore.QByteArray(), QtCore.QByteArray)
        if not self._dialog.qt.restoreGeometry(geometry):
            self._dialog.qt.resize(800, 600)

    def writeSettings(self) -> None:
        settings = QtCore.QSettings()
        geometry = self._dialog.qt.saveGeometry()
        settings.setValue("preferences/geometry", geometry)

    def exec(self):
        self._dialog.run()
