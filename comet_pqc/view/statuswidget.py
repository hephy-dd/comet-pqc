from typing import Dict, Optional

from PyQt5 import QtCore, QtWidgets

__all__ = ["StatusWidget"]


class StatusWidget(QtWidgets.QWidget):

    LightStates: Dict = {True: "ON", False: "OFF", None: "n/a"}
    DoorStates: Dict = {True: "OPEN", False: "CLOSED", None: "n/a"}

    reloadClicked = QtCore.pyqtSignal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.matrixModelLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.matrixModelLineEdit.setReadOnly(True)

        self.matrixChannelsLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.matrixChannelsLineEdit.setReadOnly(True)

        self.hvsrcModelLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.hvsrcModelLineEdit.setReadOnly(True)

        self.vsrcModelLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.vsrcModelLineEdit.setReadOnly(True)

        self.lcrModelLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.lcrModelLineEdit.setReadOnly(True)

        self.elmModelLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.elmModelLineEdit.setReadOnly(True)

        self.tableModelLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.tableModelLineEdit.setReadOnly(True)

        self.tableStateLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.tableStateLineEdit.setReadOnly(True)

        self.environModelLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit(self)
        self.environModelLineEdit.setReadOnly(True)

        self.reloadButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.reloadButton.setText("&Reload")
        self.reloadButton.clicked.connect(self.reloadClicked.emit)

        self.matrixGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.matrixGroupBox.setTitle("Matrix")

        matrixGroupBoxLayout: QtWidgets.QFormLayout = QtWidgets.QFormLayout(self.matrixGroupBox)
        matrixGroupBoxLayout.addRow("Model", self.matrixModelLineEdit)
        matrixGroupBoxLayout.addRow("Closed channels", self.matrixChannelsLineEdit)

        self.hvsrcGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.hvsrcGroupBox.setTitle("HV Source")

        hvsrcGroupBoxLayout: QtWidgets.QFormLayout = QtWidgets.QFormLayout(self.hvsrcGroupBox)
        hvsrcGroupBoxLayout.addRow("Model", self.hvsrcModelLineEdit)

        self.vsrcGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.vsrcGroupBox.setTitle("V Source")

        vsrcGroupBoxLayout: QtWidgets.QFormLayout = QtWidgets.QFormLayout(self.vsrcGroupBox)
        vsrcGroupBoxLayout.addRow("Model", self.vsrcModelLineEdit)

        self.lcrGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.lcrGroupBox.setTitle("LCR Meter")

        lcrGroupBoxLayout: QtWidgets.QFormLayout = QtWidgets.QFormLayout(self.lcrGroupBox)
        lcrGroupBoxLayout.addRow("Model", self.lcrModelLineEdit)

        self.elmGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.elmGroupBox.setTitle("Electrometer")

        elmGroupBoxLayout: QtWidgets.QFormLayout = QtWidgets.QFormLayout(self.elmGroupBox)
        elmGroupBoxLayout.addRow("Model", self.elmModelLineEdit)

        self.tableGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.tableGroupBox.setTitle("Table")

        tableGroupBoxLayout: QtWidgets.QFormLayout = QtWidgets.QFormLayout(self.tableGroupBox)
        tableGroupBoxLayout.addRow("Model", self.tableModelLineEdit)
        tableGroupBoxLayout.addRow("State", self.tableStateLineEdit)

        self.environGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.environGroupBox.setTitle("Environment Box")

        environGroupBoxLayout: QtWidgets.QFormLayout = QtWidgets.QFormLayout(self.environGroupBox)
        environGroupBoxLayout.addRow("Model", self.environModelLineEdit)

        layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self)
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
        self.matrixModelLineEdit.clear()
        self.matrixChannelsLineEdit.clear()
        self.hvsrcModelLineEdit.clear()
        self.vsrcModelLineEdit.clear()
        self.lcrModelLineEdit.clear()
        self.elmModelLineEdit.clear()
        self.tableModelLineEdit.clear()
        self.tableStateLineEdit.clear()
        self.environModelLineEdit.clear()

    def updateStatus(self, status: Dict[str, str]) -> None:
        default: str = "n/a"
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
