import math

from PyQt5 import QtWidgets

from comet import ui

from ..components import PositionWidget
from ..core.position import Position
from .panel import BasicPanel

__all__ = ["ContactPanel"]


class ContactPanel(BasicPanel):

    type = "contact"

    def __init__(self, *args, table_move=None, table_contact=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.table_move = table_move
        self.table_contact = table_contact
        self.use_table = False
        self._position_valid = False
        self._position_widget = PositionWidget()
        self._position_widget.title = "Contact Position"

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
        centralLayout.addWidget(self._position_widget.qt)
        centralLayout.addWidget(self.tableControlGroupBox)
        centralLayout.addStretch(1)

        self.layout().insertLayout(2, centralLayout)

    def update_use_table(self, enabled):
        self.use_table = enabled
        self.moveButton.setEnabled(self._position_valid and self.use_table)
        self.contactButton.setEnabled(self._position_valid and self.use_table)

    def update_position(self):
        if self.context is None:
            position = Position()
        else:
            position = Position(*self.context.position)
        self._position_widget.update_position(position)
        self._position_valid = not math.isnan(position.z)
        self.moveButton.setEnabled(self._position_valid and self.use_table)
        self.contactButton.setEnabled(self._position_valid and self.use_table)

    def mount(self, context):
        """Mount measurement to panel."""
        super().mount(context)
        self.setTitle(f"Contact &rarr; {context.name}")
        self.setDescription(context.description or "")
        self.update_position()

    def movePosition(self) -> None:
        self.moveButton.setEnabled(False)
        self.emit(self.table_move, self.context)

    def contactPosition(self) -> None:
        self.contactButton.setEnabled(False)
        self.emit(self.table_contact, self.context)
