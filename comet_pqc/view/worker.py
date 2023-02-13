import logging
from typing import Callable

from PyQt5 import QtCore

__all__ = ["Worker"]


class Worker(QtCore.QObject):

    failed = QtCore.pyqtSignal(Exception)
    finished = QtCore.pyqtSignal()

    def __init__(self, target: Callable) -> None:
        super().__init__()
        self.target = target

    def run(self):
        self.target()

    def __call__(self) -> None:
        try:
            self.run()
        except Exception as exc:
            logging.exception(exc)
            self.failed.emit()
        finally:
            self.finished.emit()
