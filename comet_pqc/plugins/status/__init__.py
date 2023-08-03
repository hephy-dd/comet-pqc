import threading
from typing import Optional

from PyQt5 import QtCore, QtWidgets

from .worker import StatusWorker

__all__ = ["StatusPlugin"]


class StatusPlugin:

    def __init__(self, window) -> None:
        self.window = window
        self.thread = None

    def on_install(self) -> None:
        self.statusWidget = StatusWidget()
        self.statusWidget.reloadClicked.connect(self.start_worker)
        self.window.addPage(self.statusWidget, "Status")

    def on_uninstall(self) -> None:
        self.window.removePage(self.statusWidget)
        self.statusWidget.deleteLater()

    def on_lock_controls(self, state: bool) -> None:
        self.statusWidget.setLocked(state)

    def start_worker(self) -> None:
        self.window.dashboard.setControlsLocked(True)
        self.statusWidget.clearStatus()
        worker = StatusWorker(self.window.station)
        worker.messageChanged.connect(self.window.showMessage)
        worker.progressChanged.connect(self.window.showProgress)
        worker.dataChanged.connect(self.worker_update_data)
        worker.failed.connect(self.window.showException)
        worker.finished.connect(self.worker_finished)
        worker.finished.connect(worker.deleteLater)
        worker.config.update({
            "use_environ": self.window.dashboard.isEnvironmentEnabled(),
            "use_table": self.window.dashboard.isTableEnabled(),
        })
        self.thread = threading.Thread(target=worker)
        self.thread.start()
        # Fix: stay in status tab
        self.window.dashboard.tabWidget.setCurrentWidget(self.statusWidget)

    def worker_update_data(self, data) -> None:
        self.statusWidget.updateStatus(data)

    def worker_finished(self) -> None:
        self.statusWidget.setLocked(False)
        self.window.dashboard.setControlsLocked(False)


class StatusWidget(QtWidgets.QWidget):

    LightStates = {True: "ON", False: "OFF", None: "n/a"}
    DoorStates = {True: "OPEN", False: "CLOSED", None: "n/a"}

    reloadClicked = QtCore.pyqtSignal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.matrixModelLineEdit = QtWidgets.QLineEdit()
        self.matrixModelLineEdit.setReadOnly(True)

        self.matrixChannelsLineEdit = QtWidgets.QLineEdit()
        self.matrixChannelsLineEdit.setReadOnly(True)

        self.hvSourceModelLineEdit = QtWidgets.QLineEdit()
        self.hvSourceModelLineEdit.setReadOnly(True)

        self.vSourceModelLineEdit = QtWidgets.QLineEdit()
        self.vSourceModelLineEdit.setReadOnly(True)

        self.lcrModelLineEdit = QtWidgets.QLineEdit()
        self.lcrModelLineEdit.setReadOnly(True)

        self.elmModelLineEdit = QtWidgets.QLineEdit()
        self.elmModelLineEdit.setReadOnly(True)

        self.tableModelLineEdit = QtWidgets.QLineEdit()
        self.tableModelLineEdit.setReadOnly(True)

        self.tableStateLineEdit = QtWidgets.QLineEdit()
        self.tableStateLineEdit.setReadOnly(True)

        self.envModelLineEdit = QtWidgets.QLineEdit()
        self.envModelLineEdit.setReadOnly(True)

        self.reloadButton = QtWidgets.QPushButton()
        self.reloadButton.setText("&Reload")
        self.reloadButton.clicked.connect(self.reloadClicked.emit)

        matrixGroupBox = QtWidgets.QGroupBox()
        matrixGroupBox.setTitle("Matrix")

        matrixGroupBoxLayout = QtWidgets.QFormLayout(matrixGroupBox)
        matrixGroupBoxLayout.addRow("Model", self.matrixModelLineEdit)
        matrixGroupBoxLayout.addRow("Closed channels", self.matrixChannelsLineEdit)

        hvSourceGroupBox = QtWidgets.QGroupBox()
        hvSourceGroupBox.setTitle("HVSource")

        hvSourceGroupBoxLayout = QtWidgets.QFormLayout(hvSourceGroupBox)
        hvSourceGroupBoxLayout.addRow("Model", self.hvSourceModelLineEdit)

        vSourceGroupBox = QtWidgets.QGroupBox()
        vSourceGroupBox.setTitle("VSource")

        vSourceGroupBoxLayout = QtWidgets.QFormLayout(vSourceGroupBox)
        vSourceGroupBoxLayout.addRow("Model", self.vSourceModelLineEdit)

        lcrGroupBox = QtWidgets.QGroupBox()
        lcrGroupBox.setTitle("LCRMeter")

        lcrGroupBoxLayout = QtWidgets.QFormLayout(lcrGroupBox)
        lcrGroupBoxLayout.addRow("Model", self.lcrModelLineEdit)

        elmGroupBox = QtWidgets.QGroupBox()
        elmGroupBox.setTitle("Electrometer")

        elmGroupBoxLayout = QtWidgets.QFormLayout(elmGroupBox)
        elmGroupBoxLayout.addRow("Model", self.elmModelLineEdit)

        tableGroupBox = QtWidgets.QGroupBox()
        tableGroupBox.setTitle("Table")

        tableGroupBoxLayout = QtWidgets.QFormLayout(tableGroupBox)
        tableGroupBoxLayout.addRow("Model", self.tableModelLineEdit)
        tableGroupBoxLayout.addRow("State", self.tableStateLineEdit)

        environGroupBox = QtWidgets.QGroupBox()
        environGroupBox.setTitle("Environment Box")

        environGroupBoxLayout = QtWidgets.QFormLayout(environGroupBox)
        environGroupBoxLayout.addRow("Model", self.envModelLineEdit)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(matrixGroupBox)
        layout.addWidget(hvSourceGroupBox)
        layout.addWidget(vSourceGroupBox)
        layout.addWidget(lcrGroupBox)
        layout.addWidget(elmGroupBox)
        layout.addWidget(tableGroupBox)
        layout.addWidget(environGroupBox)
        layout.addStretch(1)
        layout.addWidget(self.reloadButton)

    def clearStatus(self):
        self.matrixModelLineEdit.clear()
        self.matrixChannelsLineEdit.clear()
        self.hvSourceModelLineEdit.clear()
        self.vSourceModelLineEdit.clear()
        self.lcrModelLineEdit.clear()
        self.elmModelLineEdit.clear()
        self.tableModelLineEdit.clear()
        self.tableStateLineEdit.clear()
        self.envModelLineEdit.clear()

    def updateStatus(self, data: dict):
        default = "n/a"
        self.matrixModelLineEdit.setText(data.get("matrix_model", default))
        self.matrixChannelsLineEdit.setText(data.get("matrix_channels", ""))
        self.hvSourceModelLineEdit.setText(data.get("hvsrc_model", default))
        self.vSourceModelLineEdit.setText(data.get("vsrc_model", default))
        self.lcrModelLineEdit.setText(data.get("lcr_model", default))
        self.elmModelLineEdit.setText(data.get("elm_model", default))
        self.tableModelLineEdit.setText(data.get("table_model", default))
        self.tableStateLineEdit.setText(data.get("table_state", default))
        self.envModelLineEdit.setText(data.get("env_model", default))

    def setLocked(self, state: bool) -> None:
        self.reloadButton.setEnabled(not state)
