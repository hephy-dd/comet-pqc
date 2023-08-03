import logging

from PyQt5 import QtCore

from comet.driver.keithley import K707B
from comet.resource import ResourceError

__all__ = ["StatusWorker"]


class StatusWorker(QtCore.QObject):
    """Reload instruments status."""

    messageChanged = QtCore.pyqtSignal(str)
    progressChanged = QtCore.pyqtSignal(int, int)
    dataChanged = QtCore.pyqtSignal(dict)
    finished = QtCore.pyqtSignal()
    failed = QtCore.pyqtSignal(Exception)

    def __init__(self, station) -> None:
        super().__init__()
        self.station = station
        self.config: dict = {}
        self.data: dict = {}

    def updateMessage(self, message: str) -> None:
        self.messageChanged.emit(message)

    def updateProgress(self, value: float, maximum: float) -> None:
        self.progressChanged.emit(value, maximum)

    def read_matrix(self):
        self.data.update({"matrix_model": ""})
        self.data.update({"matrix_channels": ""})
        try:
            with self.station.matrix_resource as matrix_res:
                matrix = K707B(matrix_res)
                model = matrix.identification
                self.data.update({"matrix_model": model})
                channels = matrix.channel.getclose()
                self.data.update({"matrix_channels": ",".join(channels)})
        except (ResourceError, OSError):
            ...
        self.dataChanged.emit(self.data.copy())

    def read_hvsrc(self):
        self.data.update({"hvsrc_model": ""})
        try:
            with self.station.hvsrc_resource as hvsrc_res:
                model = hvsrc_res.query("*IDN?")
                self.data.update({"hvsrc_model": model})
        except (ResourceError, OSError):
            ...
        self.dataChanged.emit(self.data.copy())

    def read_vsrc(self):
        self.data.update({"vsrc_model": ""})
        try:
            with self.station.vsrc_resource as vsrc_res:
                model = vsrc_res.query("*IDN?")
                self.data.update({"vsrc_model": model})
        except (ResourceError, OSError):
            ...
        self.dataChanged.emit(self.data.copy())

    def read_lcr(self):
        self.data.update({"lcr_model": ""})
        try:
            with self.station.lcr_resource as lcr_res:
                model = lcr_res.query("*IDN?")
                self.data.update({"lcr_model": model})
        except (ResourceError, OSError):
            ...
        self.dataChanged.emit(self.data.copy())

    def read_elm(self):
        self.data.update({"elm_model": ""})
        try:
            with self.station.elm_resource as elm_res:
                model = elm_res.query("*IDN?")
                self.data.update({"elm_model": model})
        except (ResourceError, OSError):
            ...
        self.dataChanged.emit(self.data.copy())

    def read_table(self):
        self.data.update({"table_model": ""})
        self.data.update({"table_state": ""})
        if self.config.get("use_table", False):
            try:
                table_process = self.station.table_process
                model = table_process.get_identification().get(timeout=5.0)
                caldone = table_process.get_caldone().get(timeout=5.0)
                self.data.update({"table_model": model})
                if caldone == (3, 3, 3):
                    state = "CALIBRATED"
                else:
                    state = "NOT CALIBRATED"
                self.data.update({"table_state": state})
            except (ResourceError, OSError):
                ...
        self.dataChanged.emit(self.data.copy())

    def read_environ(self):
        self.data.update({"env_model": ""})
        self.data.update({"env_pc_data": None})
        if self.config.get("use_environ", False):
            try:
                with self.station.environ_process as environment:
                    model = environment.identification()
                    self.data.update({"env_model": model})
                    pc_data = environment.pc_data()
                    self.data.update({"env_pc_data": pc_data})
            except (ResourceError, OSError):
                ...
        self.dataChanged.emit(self.data.copy())

    def __call__(self) -> None:
        try:
            self.data.clear()

            self.updateMessage("Reading Matrix...")
            self.updateProgress(0, 7)
            self.read_matrix()

            self.updateMessage("Reading HVSource...")
            self.updateProgress(1, 7)
            self.read_hvsrc()

            self.updateMessage("Read VSource...")
            self.updateProgress(2, 7)
            self.read_vsrc()

            self.updateMessage("Read LCRMeter...")
            self.updateProgress(3, 7)
            self.read_lcr()

            self.updateMessage("Read Electrometer...")
            self.updateProgress(4, 7)
            self.read_elm()

            self.updateMessage("Read Table...")
            self.updateProgress(5, 7)
            self.read_table()

            self.updateMessage("Read Environment Box...")
            self.updateProgress(6, 7)
            self.read_environ()

            self.updateMessage("")
            self.updateProgress(7, 7)
        except Exception as exc:
            logging.exception(exc)
            self.failed.emit(exc)
        finally:
            self.finished.emit()
