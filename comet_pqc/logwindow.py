import logging
import threading

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

import comet

__all__ = ['LogWidget']

class LogHandler(logging.Handler):

    def __init__(self, context=None):
        super().__init__()
        self.context = context

    def emit(self, record):
        self.context.emit('message', record)

class LogItem(comet.TreeItem):

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
        self.record = record
        self[self.TimeColumn].value = self.format_time(record.created)
        self[self.LevelColumn].value = record.levelname
        self[self.MessageColumn].value = record.getMessage()
        color = self.Colors.get(record.levelno)
        self[self.TimeColumn].color = color
        self[self.LevelColumn].color = color
        self[self.MessageColumn].color = color

    @classmethod
    def format_time(cls, seconds):
        dt = QtCore.QDateTime.fromMSecsSinceEpoch(seconds * 1000)
        return dt.toString("yyyy-MM-dd hh:mm:ss")

    def __str__(self):
        return "\t".join((self[self.TimeColumn].value, self[self.LevelColumn].value, self[self.MessageColumn].value))

class LogWidget(comet.Tree):

    def __init__(self):
        super().__init__()
        self.header = "Time", "Level", "Message"
        self.indentation = 0
        self.mutex = threading.RLock()
        self.message = self.append_record
        self.handler = LogHandler(context=self)
        self.level = logging.INFO
        self.qt.setColumnWidth(0, 128)
        self.qt.setColumnWidth(1, 64)
        self.qt.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.qt.customContextMenuRequested.connect(self.on_context_menu)

    def on_context_menu(self, pos):
        item = self.qt.itemAt(pos)
        if item:
            def set_clipboard():
                text = format(item.data(0, item.UserType))
                QtWidgets.QApplication.clipboard().setText(text)
            menu = QtWidgets.QMenu(self.qt)
            copyAction = QtWidgets.QAction("&Copy")
            copyAction.setShortcut("Ctrl+C")
            copyAction.triggered.connect(set_clipboard)
            menu.addAction(copyAction)
            menu.exec(self.qt.mapToGlobal(pos))

    @property
    def level(self):
        return self.handler.level()

    @level.setter
    def level(self, value):
        self.handler.setLevel(value)

    def add_logger(self, logger):
        logger.addHandler(self.handler)

    def remove_logger(self, logger):
        logger.removeHandler(self.handler)

    def append_record(self, record):
        with self.mutex:
            item = LogItem(record)
            self.append(item)
            self.scroll_to(item)

    def dump(self):
        records = []
        for item in self:
            records.append(item.record)
        return records

    def load(self, records):
        for record in records:
            self.append_record(record)
