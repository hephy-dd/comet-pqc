import datetime
import logging

import comet

__all__ = ['LogView']

class LogView(comet.Tree):

    def __init__(self):
        super().__init__()
        self.title = "Logging"
        self.header = "Time", "Level", "Message"
        self.indentation = 0

    def append(self, record):
        dt = datetime.datetime.fromtimestamp(record.created).replace(microsecond=0)
        item = super().append([dt.isoformat(), record.levelname, record.msg])
        for i in range(len(item)):
            if record.levelno == logging.WARNING:
                item[i].color = "orange"
            if record.levelno == logging.ERROR:
                item[i].color = "red"
        self.fit()
        self.qt.scrollToItem(item.qt)
