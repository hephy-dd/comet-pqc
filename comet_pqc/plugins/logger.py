import logging
import math
import os
import threading
from datetime import datetime

from PyQt5 import QtCore, QtGui, QtWidgets

__all__ = ["LoggerPlugin"]


class LoggerPlugin:

    def __init__(self, window):
        self.window = window

    def install(self):
        self.logWidget = LogTreeWidget()
        self.logWidget.add_logger(logging.getLogger())
        self.window.addPage(self.logWidget, "Logging")

    def uninstall(self):
        self.window.removePage(self.logWidget)
        self.logWidget.deleteLater()


def format_time(seconds: float) -> str:
    # Note: occasional crashes due to `NaN` timestamp.
    if not math.isfinite(seconds):
        seconds = 0
    dt = datetime.fromtimestamp(seconds)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


class LogHandler(logging.Handler):

    def __init__(self, callback):
        super().__init__()
        self._callback = callback

    def emit(self, record):
        self._callback(record)


class LogItem(QtWidgets.QTreeWidgetItem):

    TimeColumn = 0
    LevelColumn = 1
    MessageColumn = 2

    Colors = {
        logging.DEBUG: "grey",
        logging.INFO: "black",
        logging.WARNING: "orange",
        logging.ERROR: "red"
    }

    def __init__(self, record):
        super().__init__()
        self.load_record(record)

    def load_record(self, record):
        self.setText(self.TimeColumn, format_time(record.created))
        self.setText(self.LevelColumn, record.levelname)
        self.setText(self.MessageColumn, record.getMessage())
        color = QtGui.QColor(self.Colors.get(record.levelno))
        self.setForeground(self.TimeColumn, color)
        self.setForeground(self.LevelColumn, color)
        self.setForeground(self.MessageColumn, color)


class LogTreeWidget(QtWidgets.QTreeWidget):

    handleRecord = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["Time", "Level", "Message"])
        self.setRootIsDecorated(False)
        self.mutex = threading.RLock()
        self.handleRecord.connect(self.append_record)
        self.handler = LogHandler(self.handleRecord.emit)
        self.set_level(logging.INFO)
        self.setSelectionMode(self.ContiguousSelection)
        self.setAutoScroll(True)
        self.setColumnWidth(0, 132)
        self.setColumnWidth(1, 64)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)

    def on_clipboard(self):
        """Copy selected items to clipboard."""
        items = self.selectedItems()
        if items:
            text = os.linesep.join([format(item.reflection()) for item in items])
            QtWidgets.QApplication.clipboard().setText(text)

    def on_context_menu(self, pos):
        """Provide custom context menu."""
        menu = QtWidgets.QMenu(self)
        copyAction = QtWidgets.QAction("&Copy to clipboard")
        copyAction.triggered.connect(self.on_clipboard)
        menu.addAction(copyAction)
        menu.exec(self.mapToGlobal(pos))

    def level(self):
        """Logging level for log window.

        >>> window.set_level(logging.INFO)
        """
        return self.handler.level()

    def set_level(self, value):
        self.handler.setLevel(value)

    def add_logger(self, logger):
        """Add logger to log window.

        >>> window.add_logger(logging.getLogger("root"))
        """
        logger.addHandler(self.handler)

    def remove_logger(self, logger):
        """Remove logger from log window.

        >>> window.remove_logger(logging.getLogger("root"))
        """
        logger.removeHandler(self.handler)

    def append_record(self, record):
        """Append logging record to log window."""
        with self.mutex:
            item = LogItem(record)
            self.addTopLevelItem(item)
            scroll_bar = self.verticalScrollBar()
            if scroll_bar.value() >= scroll_bar.maximum():
                self.scrollToItem(item)
