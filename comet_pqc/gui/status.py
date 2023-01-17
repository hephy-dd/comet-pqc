from typing import Dict, Optional

from PyQt5 import QtCore, QtWidgets

__all__ = ["StatusWidget"]


class StatusWidget(QtWidgets.QWidget):

    LightStates = {True: "ON", False: "OFF", None: "n/a"}
    DoorStates = {True: "OPEN", False: "CLOSED", None: "n/a"}

    reloadClicked = QtCore.pyqtSignal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.matrixModelLineEdit = QtWidgets.QLineEdit(self)
        self.matrixModelLineEdit.setReadOnly(True)

        self.matrixChannelsLineEdit = QtWidgets.QLineEdit(self)
        self.matrixChannelsLineEdit.setReadOnly(True)

        self.hvsrcModelLineEdit = QtWidgets.QLineEdit(self)
        self.hvsrcModelLineEdit.setReadOnly(True)

        self.vsrcModelLineEdit = QtWidgets.QLineEdit(self)
        self.vsrcModelLineEdit.setReadOnly(True)

        self.lcrModelLineEdit = QtWidgets.QLineEdit(self)
        self.lcrModelLineEdit.setReadOnly(True)

        self.elmModelLineEdit = QtWidgets.QLineEdit(self)
        self.elmModelLineEdit.setReadOnly(True)

        self.tableModelLineEdit = QtWidgets.QLineEdit(self)
        self.tableModelLineEdit.setReadOnly(True)

        self.tableStateLineEdit = QtWidgets.QLineEdit(self)
        self.tableStateLineEdit.setReadOnly(True)

        self.environModelLineEdit = QtWidgets.QLineEdit(self)
        self.environModelLineEdit.setReadOnly(True)

        self.reloadButton = QtWidgets.QPushButton(self)
        self.reloadButton.setText("&Reload")
        self.reloadButton.clicked.connect(self.reloadClicked.emit)

        self.matrixGroupBox = QtWidgets.QGroupBox(self)
        self.matrixGroupBox.setTitle("Matrix")

        matrixLayout = QtWidgets.QFormLayout(self.matrixGroupBox)
        matrixLayout.addRow("Model", self.matrixModelLineEdit)
        matrixLayout.addRow("Closed channels", self.matrixChannelsLineEdit)

        self.hvsrcGroupBox = QtWidgets.QGroupBox(self)
        self.hvsrcGroupBox.setTitle("HV Source")

        hvsrcLayout = QtWidgets.QFormLayout(self.hvsrcGroupBox)
        hvsrcLayout.addRow("Model", self.hvsrcModelLineEdit)

        self.vsrcGroupBox = QtWidgets.QGroupBox(self)
        self.vsrcGroupBox.setTitle("V Source")

        vsrcLayout = QtWidgets.QFormLayout(self.vsrcGroupBox)
        vsrcLayout.addRow("Model", self.vsrcModelLineEdit)

        self.lcrGroupBox = QtWidgets.QGroupBox(self)
        self.lcrGroupBox.setTitle("LCR Meter")

        lcrLayout = QtWidgets.QFormLayout(self.lcrGroupBox)
        lcrLayout.addRow("Model", self.lcrModelLineEdit)

        self.elmGroupBox = QtWidgets.QGroupBox(self)
        self.elmGroupBox.setTitle("Electrometer")

        elmLayout = QtWidgets.QFormLayout(self.elmGroupBox)
        elmLayout.addRow("Model", self.elmModelLineEdit)

        self.tableGroupBox = QtWidgets.QGroupBox(self)
        self.tableGroupBox.setTitle("Table")

        tableLayout = QtWidgets.QFormLayout(self.tableGroupBox)
        tableLayout.addRow("Model", self.tableModelLineEdit)
        tableLayout.addRow("State", self.tableStateLineEdit)

        self.environGroupBox = QtWidgets.QGroupBox(self)
        self.environGroupBox.setTitle("Environment Box")

        tableLayout = QtWidgets.QFormLayout(self.environGroupBox)
        tableLayout.addRow("Model", self.environModelLineEdit)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.matrixGroupBox)
        layout.addWidget(self.hvsrcGroupBox)
        layout.addWidget(self.vsrcGroupBox)
        layout.addWidget(self.lcrGroupBox)
        layout.addWidget(self.elmGroupBox)
        layout.addWidget(self.tableGroupBox)
        layout.addWidget(self.environGroupBox)
        layout.addStretch()
        layout.addWidget(self.reloadButton)

    def reset(self) -> None:
        self.matrixModelLineEdit.setText("")
        self.matrixChannelsLineEdit.setText("")
        self.hvsrcModelLineEdit.setText("")
        self.vsrcModelLineEdit.setText("")
        self.lcrModelLineEdit.setText("")
        self.elmModelLineEdit.setText("")
        self.tableModelLineEdit.setText("")
        self.tableStateLineEdit.setText("")
        self.environModelLineEdit.setText("")

    def updateStatus(self, status: Dict[str, str]):
        default = "n/a"
        self.matrixModelLineEdit.setText(status.get("matrix_model") or default)
        self.matrixChannelsLineEdit.setText(status.get("matrix_channels"))
        self.hvsrcModelLineEdit.setText(status.get("hvsrc_model") or default)
        self.vsrcModelLineEdit.setText(status.get("vsrc_model") or default)
        self.lcrModelLineEdit.setText(status.get("lcr_model") or default)
        self.elmModelLineEdit.setText(status.get("elm_model") or default)
        self.tableModelLineEdit.setText(status.get("table_model") or default)
        self.tableStateLineEdit.setText(status.get("table_state") or default)
        self.environModelLineEdit.setText(status.get("env_model") or default)

    def setLocked(self, state: bool) -> None:
        self.reloadButton.setEnabled(not state)
