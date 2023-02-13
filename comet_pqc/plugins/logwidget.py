import logging
import math
import os
from datetime import datetime
from typing import Callable, Dict

from PyQt5 import QtCore, QtGui, QtWidgets

from . import Plugin

__all__ = ["LogWidgetPlugin"]


class LogWidgetPlugin(Plugin):

    def install(self, window):
        self.window = window
        self.rootLogger = logging.getLogger()
        self.logWidget = LogWidget()
        self.logWidget.addLogger(self.rootLogger)
        self.widget: QtWidgets.QWidget = QtWidgets.QWidget()
        layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.widget)
        layout.addWidget(self.logWidget)
        self.window.dashboard.addTabWidget(self.widget, "Logger")

        # self.before = lambda dialog: QtWidgets.QMessageBox.information(self.window, "before", "before")
        # self.after = lambda dialog: QtWidgets.QMessageBox.information(self.window, "after", "after")
        # self.window.beforePreferences.append(self.before)
        # self.window.afterPreferences.append(self.after)

    def uninstall(self, window):
        self.logWidget.removeLogger(self.rootLogger)
        self.window.dashboard.removeTabWidget(self.widget)
        # self.window.beforePreferences.remove(self.window.beforePreferences.index(self.before))
        # self.window.afterPreferences.remove(self.window.beforePreferences.index(self.after))
        del self.logWidget
        del self.widget
        del self.window


class LogHandler(logging.Handler):

    def __init__(self, context: Callable) -> None:
        super().__init__()
        self.context: Callable = context

    def emit(self, record) -> None:
        self.context(record)


class LogItem(QtWidgets.QTreeWidgetItem):

    Colors: Dict[int, str] = {
        logging.DEBUG: "grey",
        logging.INFO: "black",
        logging.WARNING: "orange",
        logging.ERROR: "red"
    }

    def __init__(self, record: logging.LogRecord) -> None:
        super().__init__()
        self.loadRecord(record)

    def loadRecord(self, record: logging.LogRecord) -> None:
        self.setText(0, self.formatTime(record.created))
        self.setText(1, record.levelname)
        self.setText(2, record.getMessage())
        color = QtGui.QColor(self.Colors.get(record.levelno, "black"))
        self.setForeground(0, color)
        self.setForeground(1, color)
        self.setForeground(2, color)

    @classmethod
    def formatTime(cls, seconds: float) -> str:
        # Note: occasional crashes due to `NaN` timestamp.
        if not math.isfinite(seconds):
            seconds = 0
        dt = datetime.fromtimestamp(seconds)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def __str__(self) -> str:
        return "\t".join((self.text(0), self.text(1), self.text(2)))


class LogWidget(QtWidgets.QTreeWidget):

    received = QtCore.pyqtSignal(logging.LogRecord)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.handler = LogHandler(self.received.emit)
        self.setHeaderLabels(["Time", "Level", "Message"])
        self.setRootIsDecorated(False)
        self.setSelectionMode(QtWidgets.QTreeWidget.ContiguousSelection)
        self.setAutoScroll(True)
        self.setColumnWidth(0, 132)
        self.setColumnWidth(1, 64)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)
        self.received.connect(self.appendRecord)

    def copyToClipboard(self) -> None:
        """Copy selected items to clipboard."""
        items = self.selectedItems()
        if items:
            text = os.linesep.join([format(item) for item in items])
            QtWidgets.QApplication.clipboard().setText(text)

    def showContextMenu(self, pos: QtCore.QPoint) -> None:
        """Provide custom context menu."""
        menu: QtWidgets.QMenu = QtWidgets.QMenu(self)
        copyAction: QtWidgets.QAction = QtWidgets.QAction("&Copy to clipboard")
        copyAction.triggered.connect(self.copyToClipboard)
        menu.addAction(copyAction)
        menu.exec(self.mapToGlobal(pos))

    def level(self) -> int:
        return self.handler.level

    def setLevel(self, level: int) -> None:
        """Set level of log window."""
        self.handler.setLevel(level)

    def addLogger(self, logger: logging.Logger) -> None:
        """Add logger to log window."""
        logger.addHandler(self.handler)

    def removeLogger(self, logger: logging.Logger) -> None:
        """Remove logger from log window. """
        logger.removeHandler(self.handler)

    def appendRecord(self, record: logging.LogRecord) -> None:
        """Append logging record to log window."""
        item = LogItem(record)
        self.addTopLevelItem(item)
        scrollBar = self.verticalScrollBar()
        if scrollBar.value() >= scrollBar.maximum():
            self.scrollToItem(item)
