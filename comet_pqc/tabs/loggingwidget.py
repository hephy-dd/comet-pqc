import datetime
import logging
import math
import os
import threading

from PyQt5 import QtCore, QtGui, QtWidgets

__all__ = ["LoggingWidget"]


class LogHandler(logging.Handler):

    def __init__(self, context=None):
        super().__init__()
        self.context = context

    def emit(self, record):
        self.context.emit(record)


class LoggingWidgetItem(QtWidgets.QTreeWidgetItem):

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
        super().__init__([])
        self.load_record(record)

    def load_record(self, record):
        self.setText(self.TimeColumn, self.format_time(record.created))
        self.setText(self.LevelColumn, record.levelname)
        self.setText(self.MessageColumn, record.getMessage())
        color = QtGui.QColor(self.Colors.get(record.levelno))
        self.setForeground(self.TimeColumn, color)
        self.setForeground(self.LevelColumn, color)
        self.setForeground(self.MessageColumn, color)

    @classmethod
    def format_time(cls, seconds):
        # Note: occasional crashes due to `NaN` timestamp.
        if not math.isfinite(seconds):
            seconds = 0
        dt = datetime.datetime.fromtimestamp(seconds)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def __str__(self):
        return "\t".join((self.text(self.TimeColumn), self.text(self.LevelColumn), self.text(self.MessageColumn)))


class LoggingWidget(QtWidgets.QWidget):

    message = QtCore.pyqtSignal(object)

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self.treeWidget = QtWidgets.QTreeWidget(self)
        self.treeWidget.setHeaderLabels(["Time", "Level", "Message"])
        self.treeWidget.setRootIsDecorated(False)
        self.mutex = threading.RLock()
        self.message.connect(self.appendRecord)
        self.handler = LogHandler(context=self.message)
        self.setLevel(logging.INFO)
        self.treeWidget.setSelectionMode(self.treeWidget.ContiguousSelection)
        self.treeWidget.setAutoScroll(True)
        self.treeWidget.setColumnWidth(0, 132)
        self.treeWidget.setColumnWidth(1, 64)
        self.treeWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.treeWidget.customContextMenuRequested.connect(self.showContextMenu)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.treeWidget)

    def copyToClipboard(self):
        """Copy selected items to clipboard."""
        items = self.treeWidget.selectedItems()
        if items:
            text = os.linesep.join([format(item) for item in items])
            QtWidgets.QApplication.clipboard().setText(text)

    def showContextMenu(self, pos):
        """Provide custom context menu."""
        menu = QtWidgets.QMenu(self.treeWidget)
        copyAction = QtWidgets.QAction("&Copy to clipboard")
        copyAction.triggered.connect(self.copyToClipboard)
        menu.addAction(copyAction)
        menu.exec(self.mapToGlobal(pos))

    def level(self):
        """Logging level for log window.

        >>> window.level = logging.INFO
        """
        return self.handler.level()

    def setLevel(self, value):
        self.handler.setLevel(value)

    def addLogger(self, logger):
        """Add logger to log window.

        >>> window.add_logger(logging.getLogger("root"))
        """
        logger.addHandler(self.handler)

    def removeLogger(self, logger):
        """Remove logger from log window.

        >>> window.remove_logger(logging.getLogger("root"))
        """
        logger.removeHandler(self.handler)

    def appendRecord(self, record):
        """Append logging record to log window."""
        with self.mutex:
            item = LoggingWidgetItem(record)
            self.treeWidget.addTopLevelItem(item)
            scrollBar = self.treeWidget.verticalScrollBar()
            if scrollBar.value() >= scrollBar.maximum():
                self.treeWidget.scrollToItem(item)
