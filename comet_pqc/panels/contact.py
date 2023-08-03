import math
from typing import Optional

from PyQt5 import QtCore, QtWidgets

from ..components import PositionWidget
from ..core.position import Position
from .panel import BasicPanel

__all__ = ["ContactPanel"]


class ContactPanel(BasicPanel):

    tableMoveRequested = QtCore.pyqtSignal(object)
    tableContactRequested = QtCore.pyqtSignal(object)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.isTableEnabled: bool = False
        self.isPositionValid: bool = False

        self.positionWidget = PositionWidget()
        self.positionWidget.setTitle("Contact Position")

        self.moveButton = QtWidgets.QPushButton(self)
        self.moveButton.setText("Move")
        self.moveButton.setToolTip("Move table to position with safe Z position.")
        self.moveButton.setEnabled(False)
        self.moveButton.clicked.connect(self.movePosition)

        self.contactButton = QtWidgets.QPushButton(self)
        self.contactButton.setText("Contact")
        self.contactButton.setToolTip("Move table to position and contact with sample.")
        self.contactButton.setEnabled(False)
        self.contactButton.clicked.connect(self.contactPosition)

        self.tableControlGroupBox = QtWidgets.QGroupBox(self)
        self.tableControlGroupBox.setTitle("Table Control")

        tableControlGroupBoxLayout = QtWidgets.QVBoxLayout(self.tableControlGroupBox)
        tableControlGroupBoxLayout.addWidget(self.moveButton)
        tableControlGroupBoxLayout.addWidget(self.contactButton)
        tableControlGroupBoxLayout.addStretch(1)

        centralLayout = QtWidgets.QHBoxLayout()
        centralLayout.addWidget(self.positionWidget)
        centralLayout.addWidget(self.tableControlGroupBox)
        centralLayout.addStretch(1)

        self.layout().insertLayout(2, centralLayout)

    def setTableEnabled(self, enabled: bool) -> None:
        self.isTableEnabled = enabled
        self.moveButton.setEnabled(self.isPositionValid and self.isTableEnabled)
        self.contactButton.setEnabled(self.isPositionValid and self.isTableEnabled)

    def updatePosition(self) -> None:
        if self.context is None:
            position = Position()
        else:
            position = Position(*self.context.position)
        self.positionWidget.setPosition(position)
        self.isPositionValid = not math.isnan(position.z)
        self.moveButton.setEnabled(self.isPositionValid and self.isTableEnabled)
        self.contactButton.setEnabled(self.isPositionValid and self.isTableEnabled)

    def movePosition(self) -> None:
        self.moveButton.setEnabled(False)
        self.tableMoveRequested.emit(self.context)

    def contactPosition(self) -> None:
        self.contactButton.setEnabled(False)
        self.tableContactRequested.emit(self.context)

    def mount(self, context) -> None:
        """Mount measurement to panel."""
        super().mount(context)
        self.setTitle(f"Contact &rarr; {context.name()}")
        self.setDescription(context.description() or "")
        self.updatePosition()
