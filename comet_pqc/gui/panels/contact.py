import math
from typing import Optional

from PyQt5 import QtCore, QtWidgets

from comet_pqc.core.position import Position

from ..components import PositionWidget
from .panel import Panel

__all__ = ["ContactPanel"]


class ContactPanel(Panel):

    type_name = "contact"

    moveRequested: QtCore.pyqtSignal = QtCore.pyqtSignal(object)
    contactRequested: QtCore.pyqtSignal = QtCore.pyqtSignal(object)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setTitle("Contact")

        self.use_table = False
        self._position_valid = False

        self.positionWidget: PositionWidget = PositionWidget(self)
        self.positionWidget.setTitle("Contact Position")

        self.requestMoveButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.requestMoveButton.setText("Move")
        self.requestMoveButton.setStatusTip("Move table to position with safe Z position.")
        self.requestMoveButton.setEnabled(False)
        self.requestMoveButton.clicked.connect(self.requestMove)

        self.requestContactButton: QtWidgets.QPushButton = QtWidgets.QPushButton(self)
        self.requestContactButton.setText("Contact")
        self.requestContactButton.setStatusTip("Move table to position and contact with sample.")
        self.requestContactButton.setEnabled(False)
        self.requestContactButton.clicked.connect(self.requestContact)

        self.tableControlGroupBox: QtWidgets.QGroupBox = QtWidgets.QGroupBox(self)
        self.tableControlGroupBox.setTitle("Table Control")

        tableControlGroupBoxLayout = QtWidgets.QVBoxLayout(self.tableControlGroupBox)
        tableControlGroupBoxLayout.addWidget(self.requestMoveButton)
        tableControlGroupBoxLayout.addWidget(self.requestContactButton)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.positionWidget, 0)
        layout.addWidget(self.tableControlGroupBox, 0)
        layout.addStretch(1)

        self.rootLayout.addLayout(layout, 0)
        self.rootLayout.addStretch(1)

    def updateUseTable(self, enabled: bool) -> None:
        self.use_table = enabled
        isLocked = self.isLocked()
        self.requestMoveButton.setEnabled(self._position_valid and self.use_table and not isLocked)
        self.requestContactButton.setEnabled(self._position_valid and self.use_table and not isLocked)

    def updatePosition(self):
        if self.context is None:
            position = Position()
        else:
            position = Position(*self.context.position)
        self.positionWidget.updatePosition(position)
        self._position_valid = not math.isnan(position.z)
        isLocked = self.isLocked()
        self.requestMoveButton.setEnabled(self._position_valid and self.use_table and not isLocked)
        self.requestContactButton.setEnabled(self._position_valid and self.use_table and not isLocked)

    def setLocked(self, state: bool) -> None:
        super().setLocked(state)
        self.requestMoveButton.setEnabled(not state)
        self.requestContactButton.setEnabled(not state)

    def mount(self, context):
        """Mount measurement to panel."""
        super().mount(context)
        self.titleLabel.setText(f"{self.title()} &rarr; {context.name}")
        self.descriptionLabel.setText(context.description)
        self.updatePosition()

    @QtCore.pyqtSlot()
    def requestMove(self):
        self.requestMoveButton.setEnabled(False)
        self.moveRequested.emit(self.context)

    @QtCore.pyqtSlot()
    def requestContact(self):
        self.requestContactButton.setEnabled(False)
        self.contactRequested.emit(self.context)
