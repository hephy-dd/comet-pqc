import datetime
import logging
import threading

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

import comet

__all__ = ['LogWidget']

class LogHandler(QtCore.QObject, logging.Handler):

    message = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

    def emit(self, record):
        self.message.emit(record)

class LogTreeWidgetItem(QtWidgets.QTreeWidgetItem):

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
        self.setFromRecord(record)

    def setFromRecord(self, record):
        self.record = record
        self.setText(self.TimeColumn, self.formatTime(record.created))
        self.setText(self.LevelColumn, record.levelname)
        self.setText(self.MessageColumn, record.getMessage())
        brush = QtGui.QBrush(QtGui.QColor(self.Colors.get(record.levelno)))
        self.setForeground(self.TimeColumn, brush)
        self.setForeground(self.LevelColumn, brush)
        self.setForeground(self.MessageColumn, brush)

    @classmethod
    def formatTime(cls, seconds):
        dt = QtCore.QDateTime.fromMSecsSinceEpoch(seconds * 1000)
        return dt.toString("yyyy-MM-dd hh:mm:ss")

class LogTreeWidget(QtWidgets.QTreeWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mutex = threading.RLock()
        self.handler = LogHandler(self)
        self.handler.message.connect(self.appendRecord)
        self.setLevel(logging.INFO)
        self.setIndentation(0)
        self.headerItem().setText(0, self.tr("Time"))
        self.headerItem().setText(1, self.tr("Level"))
        self.headerItem().setText(2, self.tr("Message"))
        self.setColumnWidth(0, 128)
        self.setColumnWidth(1, 64)

    def setLevel(self, level):
        self.handler.setLevel(level)

    def addLogger(self, logger):
        logger.addHandler(self.handler)

    def removeLogger(self, logger):
        logger.removeHandler(self.handler)

    @QtCore.pyqtSlot(object)
    def appendRecord(self, record):
        item = LogTreeWidgetItem(record)
        with self.mutex:
            self.addTopLevelItem(item)
            self.scrollToItem(item)

class LogWidget(comet.Widget):

    QtBaseClass = LogTreeWidget

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def clear(self):
        self.qt.clear()

    def set_level(self, level):
        self.qt.setLevel(level)

    def add_logger(self, logger):
        self.qt.addLogger(logger)

    def remove_logger(self, logger):
        self.qt.removeLogger(logger)

    def dump(self):
        records = []
        for index in range(self.qt.topLevelItemCount()):
            item = self.qt.topLevelItem(index)
            records.append(item.record)
        return records

    def load(self, records):
        for record in records:
            self.qt.appendRecord(record)
