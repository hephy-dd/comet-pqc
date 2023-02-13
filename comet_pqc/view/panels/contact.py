import math
from typing import Optional

from PyQt5 import QtCore, QtWidgets

from comet_pqc.core.position import Position

from ..components import PositionWidget
from .panel import Panel

__all__ = ["ContactPanel"]


class ContactPanel(Panel):

    moveRequested = QtCore.pyqtSignal(object)
    contactRequested = QtCore.pyqtSignal(object)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.title = "Contact"

        self.isTableEnabled: bool = False  # TODO
        self.isPositionValid: bool = False  # TODO

        self.positionWidget: PositionWidget = PositionWidget(self)
        self.positionWidget.setTitle("Contact Position")

        self.moveButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.moveButton.setText("Move")
        self.moveButton.setToolTip("Move table to position with safe Z position")
        self.moveButton.setEnabled(False)
        self.moveButton.clicked.connect(self.requestMove)

        self.contactButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.contactButton.setText("Contact")
        self.contactButton.setToolTip("Move table to position and contact with sample")
        self.contactButton.setEnabled(False)
        self.contactButton.clicked.connect(self.requestContact)

        self.controlGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.controlGroupBox.setTitle("Table Control")

        # TODO obsolete?
        self.controlGroupBox.setEnabled(False)
        self.controlGroupBox.setVisible(False)

        controlGroupBoxLayout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.controlGroupBox)
        controlGroupBoxLayout.addWidget(self.moveButton)
        controlGroupBoxLayout.addWidget(self.contactButton)
        controlGroupBoxLayout.addStretch()

        layout: QtWidgets.QGridLayout = QtWidgets.QGridLayout()
        layout.addWidget(self.positionWidget, 0, 0)
        layout.addWidget(self.controlGroupBox, 0, 1)
        layout.setColumnStretch(2, 1)

        self.panelLayout.insertLayout(2, layout)
        self.panelLayout.setStretch(3, 1)

    def setTableEnabled(self, enabled: bool) -> None:
        self.isTableEnabled = enabled
        self.moveButton.setEnabled(self.isPositionValid and self.isTableEnabled and not self.isLocked())
        self.contactButton.setEnabled(self.isPositionValid and self.isTableEnabled and not self.isLocked())

    def setPosition(self, position: Position) -> None:
        self.positionWidget.setPosition(position)
        self.isPositionValid = not math.isnan(position.z)
        self.moveButton.setEnabled(self.isPositionValid and self.isTableEnabled)
        self.contactButton.setEnabled(self.isPositionValid and self.isTableEnabled)

    def mount(self, context):
        """Mount measurement to panel."""
        super().mount(context)
        self.setTitle(f"{self.title} &rarr; {context.name}")
        self.setDescription(context.description())
        self.setPosition(context.position())

    def setLocked(self, locked: bool) -> None:
        self.moveButton.setEnabled(not locked)
        self.contactButton.setEnabled(not locked)
        super().setLocked(locked)

    @QtCore.pyqtSlot()
    def requestMove(self) -> None:
        self.setLocked(True)
        self.moveRequested.emit(self.context)

    @QtCore.pyqtSlot()
    def requestContact(self) -> None:
        self.setLocked(True)
        self.contactRequested.emit(self.context)
