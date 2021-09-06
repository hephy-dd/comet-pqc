import datetime
import logging
import math
import threading
import os

from PyQt5 import QtCore
from PyQt5 import QtWidgets

from comet import ui

__all__ = ['LogWidget']

class LogHandler(logging.Handler):

    def __init__(self, context=None):
        super().__init__()
        self.context = context

    def emit(self, record):
        self.context.emit('message', record)

class LogItem(ui.TreeItem):

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
        self[self.TimeColumn].value = self.format_time(record.created)
        self[self.LevelColumn].value = record.levelname
        self[self.MessageColumn].value = record.getMessage()
        color = self.Colors.get(record.levelno)
        self[self.TimeColumn].color = color
        self[self.LevelColumn].color = color
        self[self.MessageColumn].color = color

    @classmethod
    def format_time(cls, seconds):
        # Note: occasional crashes due to `NaN` timestamp.
        if not math.isfinite(seconds):
            seconds = 0
        dt = datetime.datetime.fromtimestamp(seconds)
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    def __str__(self):
        return "\t".join((self[self.TimeColumn].value, self[self.LevelColumn].value, self[self.MessageColumn].value))

class LogWidget(ui.Tree):

    def __init__(self):
        super().__init__()
        self.header = "Time", "Level", "Message"
        self.root_is_decorated = False
        self.mutex = threading.RLock()
        self.message = self.append_record
        self.handler = LogHandler(context=self)
        self.level = logging.INFO
        self.qt.setSelectionMode(self.qt.ContiguousSelection)
        self.qt.setAutoScroll(True)
        self.qt.setColumnWidth(0, 132)
        self.qt.setColumnWidth(1, 64)
        self.qt.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.qt.customContextMenuRequested.connect(self.on_context_menu)

    def on_clipboard(self):
        """Copy selected items to clipboard."""
        items = self.qt.selectedItems()
        if items:
            text = os.linesep.join([format(item.reflection()) for item in items])
            QtWidgets.QApplication.clipboard().setText(text)

    def on_context_menu(self, pos):
        """Provide custom context menu."""
        menu = QtWidgets.QMenu(self.qt)
        copyAction = QtWidgets.QAction("&Copy to clipboard")
        copyAction.triggered.connect(self.on_clipboard)
        menu.addAction(copyAction)
        menu.exec(self.qt.mapToGlobal(pos))

    @property
    def level(self):
        """Logging level for log window.

        >>> window.level = logging.INFO
        """
        return self.handler.level()

    @level.setter
    def level(self, value):
        self.handler.setLevel(value)

    def add_logger(self, logger):
        """Add logger to log window.

        >>> window.add_logger(logging.getLogger('root'))
        """
        logger.addHandler(self.handler)

    def remove_logger(self, logger):
        """Remove logger from log window.

        >>> window.remove_logger(logging.getLogger('root'))
        """
        logger.removeHandler(self.handler)

    def append_record(self, record):
        """Append logging record to log window."""
        with self.mutex:
            item = LogItem(record)
            self.append(item)
            scroll_bar = self.qt.verticalScrollBar()
            if scroll_bar.value() >= scroll_bar.maximum():
                self.scroll_to(item)
