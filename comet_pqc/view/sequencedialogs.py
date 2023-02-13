from typing import Optional

from PyQt5 import QtCore, QtWidgets

from ..settings import settings
from .components import (OperatorWidget, PositionsComboBox,
                         WorkingDirectoryWidget)

__all__ = ["SequenceStartDialog"]


class SequenceStartDialog(QtWidgets.QDialog):
    """Start sequence dialog."""

    def __init__(self, message: str, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Start Sequence")

        self.messageLabel: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.messageLabel.setText(message)
        self.messageLabel.setWordWrap(True)

        self.contactCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.contactCheckBox.setText("Move table and contact with Probe Card")
        self.contactCheckBox.setChecked(True)

        self.positionCheckBox: QtWidgets.QCheckBox = QtWidgets.QCheckBox(self)
        self.positionCheckBox.setText("Move table after measurements")
        self.positionCheckBox.setChecked(False)
        self.positionCheckBox.stateChanged.connect(self.updateInputs)

        self.positionsComboBox: PositionsComboBox = PositionsComboBox()  # TODO
        self.positionsComboBox.setEnabled(False)

        self.tableGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.tableGroupBox.setTitle("Table")

        tableGroupBoxLayout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self.tableGroupBox)
        tableGroupBoxLayout.addWidget(self.contactCheckBox, 0, 0, 1, 2)
        tableGroupBoxLayout.addWidget(self.positionCheckBox, 1, 0, 1, 1)
        tableGroupBoxLayout.addWidget(self.positionsComboBox, 1, 1, 1, 1)

        tableGroupBoxLayout.setColumnStretch(0, 0)
        tableGroupBoxLayout.setColumnStretch(1, 1)

        self.operatorWidget: OperatorWidget = OperatorWidget(self)

        self.outputWidget: WorkingDirectoryWidget = WorkingDirectoryWidget()  # TODO
        self.outputWidget.setTitle("Working Directory")
        self.outputWidget.setMaximumWidth(400)

        self.buttonBox: QtWidgets.QDialogButtonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Yes)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.No)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Yes).setAutoDefault(False)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.No).setDefault(True)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.messageLabel, 0, 0, 1, 2)
        layout.addWidget(self.tableGroupBox, 1, 0, 1, 2)
        layout.addWidget(self.operatorWidget, 2, 0)
        layout.addWidget(self.outputWidget, 2, 1)
        layout.addWidget(self.buttonBox, 4, 0, 1, 2)

        layout.setRowStretch(3, 1)
        layout.setColumnStretch(0, 0)
        layout.setColumnStretch(1, 1)

    # Settings

    def readSettings(self) -> None:
        self.contactCheckBox.setChecked(settings.value("move_to_contact", False, bool))
        self.positionCheckBox.setChecked(settings.value("move_on_success", False, bool))
        self.positionsComboBox.readSettings()
        self.operatorWidget.readSettings()
        self.outputWidget.readSettings()

    def writeSettings(self) -> None:
        settings.setValue("move_to_contact", self.contactCheckBox.isChecked())
        settings.setValue("move_on_success", self.positionCheckBox.isChecked())
        self.positionsComboBox.writeSettings()
        self.operatorWidget.writeSettings()
        self.outputWidget.writeSettings()

    def setTableEnabled(self, enabled: bool) -> None:
        self.contactCheckBox.setEnabled(enabled)
        self.positionCheckBox.setEnabled(enabled)

    @QtCore.pyqtSlot()
    def updateInputs(self) -> None:
        self.positionsComboBox.setEnabled(self.positionCheckBox.isChecked())

    def isMoveToContact(self) -> bool:
        return self.contactCheckBox.isChecked()

    def moveToPosition(self) -> Optional[tuple]:  # TODO
        if self.isMoveToContact() and self.positionCheckBox.isChecked():
            index = self.positionsComboBox.currentIndex()
            positions = settings.table_positions()
            if 0 <= index < len(positions):
                position = positions[index]
                return position.x, position.y, position.z
        return None
